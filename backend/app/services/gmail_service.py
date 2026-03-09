"""Gmail API integration service."""

import email.utils
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.services.oauth_service import OAuthError

logger = logging.getLogger(__name__)

# Gmail API returns at most 500 per page; we use a smaller page size
_LIST_PAGE_SIZE = 100


class GmailService:
    """Fetches and parses emails from the Gmail API.

    Each instance is scoped to a single user via their OAuth credentials.
    """

    def __init__(self, credentials: Credentials) -> None:
        self._credentials = credentials
        self._service = build("gmail", "v1", credentials=credentials)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_emails(
        self,
        user_id: uuid.UUID,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> list[dict]:
        """Fetch emails from Gmail for a user.

        Args:
            user_id: The user's UUID (used for logging only).
            since: Only fetch emails received after this timestamp.
            max_results: Maximum number of emails to return.

        Returns:
            List of email dicts with keys matching EmailCreate schema.

        Raises:
            OAuthError: If Gmail rejects the credentials (401/403).
        """
        query = ""
        if since:
            epoch = int(since.timestamp())
            query = f"after:{epoch}"

        message_ids = self._list_message_ids(query, max_results, user_id)

        emails: list[dict] = []
        for msg_id in message_ids:
            email_data = self._get_message_details(msg_id)
            if email_data is not None:
                emails.append(email_data)

        logger.info(
            "Fetched %d emails for user %s (requested max %d)",
            len(emails),
            user_id,
            max_results,
        )
        return emails

    def get_email_detail(
        self, user_id: uuid.UUID, gmail_id: str
    ) -> Optional[dict]:
        """Fetch a single email's details from Gmail.

        Args:
            user_id: The user's UUID (used for logging only).
            gmail_id: The Gmail message ID.

        Returns:
            Email dict matching EmailCreate schema, or None if not found.
        """
        return self._get_message_details(gmail_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _list_message_ids(
        self, query: str, max_results: int, user_id: uuid.UUID
    ) -> list[str]:
        """Paginate messages.list to collect message IDs."""
        message_ids: list[str] = []
        page_token: Optional[str] = None

        try:
            while len(message_ids) < max_results:
                remaining = max_results - len(message_ids)
                result = (
                    self._service.users()
                    .messages()
                    .list(
                        userId="me",
                        q=query or None,
                        maxResults=min(remaining, _LIST_PAGE_SIZE),
                        pageToken=page_token,
                    )
                    .execute()
                )

                messages = result.get("messages", [])
                if not messages:
                    break

                message_ids.extend(msg["id"] for msg in messages)

                page_token = result.get("nextPageToken")
                if not page_token:
                    break
        except HttpError as exc:
            self._handle_http_error(exc, user_id)

        return message_ids[:max_results]

    def _get_message_details(self, message_id: str) -> Optional[dict]:
        """Fetch and parse a single message into an EmailCreate-compatible dict."""
        try:
            msg = (
                self._service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                )
                .execute()
            )
        except HttpError as exc:
            if exc.resp.status == 404:
                logger.warning("Message %s not found (404)", message_id)
                return None
            logger.error("Failed to fetch message %s: %s", message_id, exc)
            return None
        except Exception as exc:
            logger.error("Unexpected error fetching message %s: %s", message_id, exc)
            return None

        headers = {
            h["name"]: h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        received_at = self._parse_date(
            headers.get("Date"),
            msg.get("internalDate"),
        )
        has_attachments = self._has_attachments(msg.get("payload", {}))
        thread_length = self._get_thread_length(msg.get("threadId", ""))

        return {
            "gmail_id": message_id,
            "sender": headers.get("From", ""),
            "subject": headers.get("Subject", "(no subject)"),
            "body_preview": msg.get("snippet", ""),
            "received_at": received_at,
            "has_attachments": has_attachments,
            "thread_length": thread_length,
        }

    @staticmethod
    def _parse_date(
        date_header: Optional[str], internal_date_ms: Optional[str]
    ) -> datetime:
        """Parse a datetime from the Date header or Gmail's internalDate.

        Falls back to the current time if neither can be parsed.
        """
        # Try the Date header first
        if date_header:
            try:
                return email.utils.parsedate_to_datetime(date_header)
            except (ValueError, TypeError):
                logger.debug("Could not parse Date header: %s", date_header)

        # Fallback to internalDate (milliseconds since epoch)
        if internal_date_ms:
            try:
                epoch_seconds = int(internal_date_ms) / 1000.0
                return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
            except (ValueError, TypeError, OverflowError):
                logger.debug("Could not parse internalDate: %s", internal_date_ms)

        # Last resort
        return datetime.now(timezone.utc)

    @staticmethod
    def _has_attachments(payload: dict) -> bool:
        """Recursively check whether the payload contains attachments."""
        parts = payload.get("parts", [])
        for part in parts:
            filename = part.get("filename", "")
            if filename:
                return True
            # Recurse into nested multipart
            if GmailService._has_attachments(part):
                return True
        return False

    def _get_thread_length(self, thread_id: str) -> int:
        """Get the number of messages in a thread."""
        if not thread_id:
            return 1
        try:
            thread = (
                self._service.users()
                .threads()
                .get(userId="me", id=thread_id, format="minimal")
                .execute()
            )
            return len(thread.get("messages", []))
        except Exception as exc:
            logger.debug("Could not fetch thread %s: %s", thread_id, exc)
            return 1

    @staticmethod
    def _handle_http_error(exc: HttpError, user_id: uuid.UUID) -> None:
        """Translate Gmail API HTTP errors into appropriate exceptions."""
        status_code = exc.resp.status
        if status_code in (401, 403):
            raise OAuthError(
                "Gmail API authentication failed. Re-authentication required."
            ) from exc
        logger.error(
            "Gmail API error for user %s: %s (HTTP %d)",
            user_id,
            exc,
            status_code,
        )
        raise
