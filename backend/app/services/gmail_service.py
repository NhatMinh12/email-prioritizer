"""Gmail API integration service.

Stub implementation for Func 3a. Real Gmail API integration will be
added in Func 3b.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class GmailService:
    """Interface for Gmail email fetching.

    This is a stub implementation that returns empty results.
    The real implementation (Func 3b) will use the Google Gmail API.
    """

    def __init__(self, credentials: Optional[dict] = None) -> None:
        self._credentials = credentials

    def fetch_emails(
        self,
        user_id: uuid.UUID,
        since: Optional[datetime] = None,
        max_results: int = 50,
    ) -> list[dict]:
        """Fetch emails from Gmail for a user.

        Args:
            user_id: The user's UUID.
            since: Only fetch emails received after this timestamp.
            max_results: Maximum number of emails to return.

        Returns:
            List of email dicts with keys matching EmailCreate schema:
            gmail_id, sender, subject, body_preview, received_at,
            has_attachments, thread_length.
        """
        logger.info(
            "GmailService.fetch_emails called (stub): user=%s, since=%s, max=%d",
            user_id,
            since,
            max_results,
        )
        return []

    def get_email_detail(
        self, user_id: uuid.UUID, gmail_id: str
    ) -> Optional[dict]:
        """Fetch a single email's full details from Gmail.

        Args:
            user_id: The user's UUID.
            gmail_id: The Gmail message ID.

        Returns:
            Email dict matching EmailCreate schema, or None if not found.
        """
        logger.info(
            "GmailService.get_email_detail called (stub): user=%s, gmail_id=%s",
            user_id,
            gmail_id,
        )
        return None
