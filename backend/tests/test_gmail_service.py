"""Tests for the Gmail API service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from app.services.gmail_service import GmailService
from app.services.oauth_service import OAuthError


@pytest.fixture()
def mock_credentials():
    """Mock Google OAuth credentials."""
    return MagicMock()


@pytest.fixture()
def mock_gmail_api():
    """Mock the Gmail API service object."""
    return MagicMock()


@pytest.fixture()
def gmail_service(mock_credentials, mock_gmail_api):
    """GmailService with a mocked API client."""
    with patch("app.services.gmail_service.build", return_value=mock_gmail_api):
        service = GmailService(credentials=mock_credentials)
    return service


@pytest.fixture()
def user_id():
    return uuid.uuid4()


def _make_message(msg_id, sender="sender@example.com", subject="Test Subject",
                  snippet="Preview text", internal_date="1709900000000",
                  thread_id="thread_1", parts=None):
    """Build a Gmail API message response dict."""
    headers = [
        {"name": "From", "value": sender},
        {"name": "Subject", "value": subject},
        {"name": "Date", "value": "Fri, 08 Mar 2024 12:00:00 +0000"},
    ]
    payload = {"headers": headers}
    if parts is not None:
        payload["parts"] = parts

    return {
        "id": msg_id,
        "threadId": thread_id,
        "snippet": snippet,
        "internalDate": internal_date,
        "payload": payload,
    }


def _http_error(status_code, reason="error"):
    """Create a mock HttpError."""
    resp = MagicMock()
    resp.status = status_code
    resp.reason = reason
    return HttpError(resp=resp, content=b"error")


class TestFetchEmails:
    def test_returns_parsed_emails(self, gmail_service, mock_gmail_api, user_id):
        """Fetched emails are parsed into EmailCreate-compatible dicts."""
        mock_gmail_api.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_1"}],
        }
        mock_gmail_api.users().messages().get().execute.return_value = _make_message("msg_1")
        mock_gmail_api.users().threads().get().execute.return_value = {
            "messages": [{"id": "msg_1"}],
        }

        result = gmail_service.fetch_emails(user_id)

        assert len(result) == 1
        email = result[0]
        assert email["gmail_id"] == "msg_1"
        assert email["sender"] == "sender@example.com"
        assert email["subject"] == "Test Subject"
        assert email["body_preview"] == "Preview text"
        assert isinstance(email["received_at"], datetime)
        assert email["has_attachments"] is False
        assert email["thread_length"] == 1

    def test_with_since_filter(self, gmail_service, mock_gmail_api, user_id):
        """The 'since' parameter adds an 'after:' query to Gmail."""
        mock_gmail_api.users().messages().list().execute.return_value = {
            "messages": [],
        }
        since = datetime(2024, 3, 1, tzinfo=timezone.utc)
        gmail_service.fetch_emails(user_id, since=since)

        call_kwargs = mock_gmail_api.users().messages().list.call_args
        query = call_kwargs.kwargs.get("q") or call_kwargs[1].get("q")
        assert "after:" in query

    def test_pagination(self, gmail_service, mock_gmail_api, user_id):
        """Handles multi-page results with nextPageToken."""
        page1 = {
            "messages": [{"id": f"msg_{i}"} for i in range(3)],
            "nextPageToken": "token_page2",
        }
        page2 = {
            "messages": [{"id": f"msg_{i}"} for i in range(3, 5)],
        }
        mock_gmail_api.users().messages().list().execute.side_effect = [page1, page2]
        mock_gmail_api.users().messages().get().execute.return_value = _make_message("msg_x")
        mock_gmail_api.users().threads().get().execute.return_value = {
            "messages": [{"id": "msg_x"}],
        }

        result = gmail_service.fetch_emails(user_id, max_results=10)

        assert len(result) == 5

    def test_max_results_respected(self, gmail_service, mock_gmail_api, user_id):
        """Never returns more emails than max_results."""
        mock_gmail_api.users().messages().list().execute.return_value = {
            "messages": [{"id": f"msg_{i}"} for i in range(10)],
        }
        mock_gmail_api.users().messages().get().execute.return_value = _make_message("msg_x")
        mock_gmail_api.users().threads().get().execute.return_value = {
            "messages": [{"id": "msg_x"}],
        }

        result = gmail_service.fetch_emails(user_id, max_results=3)

        assert len(result) == 3

    def test_empty_inbox(self, gmail_service, mock_gmail_api, user_id):
        """Empty inbox returns empty list."""
        mock_gmail_api.users().messages().list().execute.return_value = {}

        result = gmail_service.fetch_emails(user_id)

        assert result == []

    def test_auth_error_raises_oauth_error(self, gmail_service, mock_gmail_api, user_id):
        """401/403 from Gmail API raises OAuthError."""
        mock_gmail_api.users().messages().list().execute.side_effect = _http_error(401)

        with pytest.raises(OAuthError):
            gmail_service.fetch_emails(user_id)

    def test_403_raises_oauth_error(self, gmail_service, mock_gmail_api, user_id):
        """403 from Gmail API raises OAuthError."""
        mock_gmail_api.users().messages().list().execute.side_effect = _http_error(403)

        with pytest.raises(OAuthError):
            gmail_service.fetch_emails(user_id)

    def test_server_error_propagates(self, gmail_service, mock_gmail_api, user_id):
        """500 from Gmail API is re-raised."""
        mock_gmail_api.users().messages().list().execute.side_effect = _http_error(500)

        with pytest.raises(HttpError):
            gmail_service.fetch_emails(user_id)


class TestGetEmailDetail:
    def test_returns_parsed_email(self, gmail_service, mock_gmail_api, user_id):
        """Single email fetch returns parsed dict."""
        mock_gmail_api.users().messages().get().execute.return_value = _make_message("msg_1")
        mock_gmail_api.users().threads().get().execute.return_value = {
            "messages": [{"id": "msg_1"}],
        }

        result = gmail_service.get_email_detail(user_id, "msg_1")

        assert result is not None
        assert result["gmail_id"] == "msg_1"
        assert result["sender"] == "sender@example.com"

    def test_not_found_returns_none(self, gmail_service, mock_gmail_api, user_id):
        """404 for a single message returns None."""
        mock_gmail_api.users().messages().get().execute.side_effect = _http_error(404)

        result = gmail_service.get_email_detail(user_id, "nonexistent")

        assert result is None


class TestParseDate:
    def test_from_date_header(self):
        """Parses standard email Date header."""
        result = GmailService._parse_date(
            "Fri, 08 Mar 2024 12:00:00 +0000", None
        )
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 8

    def test_from_internal_date(self):
        """Falls back to internalDate (ms since epoch)."""
        # 1709900000000 ms = 2024-03-08T12:53:20 UTC
        result = GmailService._parse_date(None, "1709900000000")
        assert result.year == 2024
        assert result.tzinfo is not None

    def test_invalid_date_header_falls_back_to_internal_date(self):
        """Invalid Date header falls back to internalDate."""
        result = GmailService._parse_date("not a date", "1709900000000")
        assert result.year == 2024

    def test_no_date_at_all_returns_now(self):
        """If neither source available, returns current time."""
        result = GmailService._parse_date(None, None)
        assert result.tzinfo is not None
        # Should be approximately now
        assert (datetime.now(timezone.utc) - result).total_seconds() < 5


class TestHasAttachments:
    def test_no_parts(self):
        """Payload without parts has no attachments."""
        assert GmailService._has_attachments({}) is False

    def test_parts_without_filename(self):
        """Parts without filename are not attachments."""
        payload = {"parts": [{"mimeType": "text/plain", "filename": ""}]}
        assert GmailService._has_attachments(payload) is False

    def test_parts_with_filename(self):
        """Parts with filename are attachments."""
        payload = {"parts": [{"mimeType": "application/pdf", "filename": "doc.pdf"}]}
        assert GmailService._has_attachments(payload) is True

    def test_nested_parts_with_attachment(self):
        """Recursively finds attachments in nested parts."""
        payload = {
            "parts": [
                {
                    "mimeType": "multipart/mixed",
                    "filename": "",
                    "parts": [
                        {"mimeType": "application/pdf", "filename": "nested.pdf"},
                    ],
                }
            ]
        }
        assert GmailService._has_attachments(payload) is True


class TestGetThreadLength:
    def test_returns_message_count(self, gmail_service, mock_gmail_api):
        """Returns the number of messages in a thread."""
        mock_gmail_api.users().threads().get().execute.return_value = {
            "messages": [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}],
        }

        assert gmail_service._get_thread_length("thread_1") == 3

    def test_empty_thread_id_returns_1(self, gmail_service):
        """Empty thread ID defaults to 1."""
        assert gmail_service._get_thread_length("") == 1

    def test_api_error_returns_1(self, gmail_service, mock_gmail_api):
        """API error for thread lookup defaults to 1."""
        mock_gmail_api.users().threads().get().execute.side_effect = Exception("error")

        assert gmail_service._get_thread_length("thread_1") == 1


class TestSenderParsing:
    def test_name_and_email(self, gmail_service, mock_gmail_api, user_id):
        """Parses 'Name <email>' format."""
        msg = _make_message("msg_1", sender="John Doe <john@example.com>")
        mock_gmail_api.users().messages().get().execute.return_value = msg
        mock_gmail_api.users().threads().get().execute.return_value = {
            "messages": [{"id": "msg_1"}],
        }

        result = gmail_service.get_email_detail(user_id, "msg_1")
        assert result["sender"] == "John Doe <john@example.com>"

    def test_email_only(self, gmail_service, mock_gmail_api, user_id):
        """Handles bare email address."""
        msg = _make_message("msg_1", sender="john@example.com")
        mock_gmail_api.users().messages().get().execute.return_value = msg
        mock_gmail_api.users().threads().get().execute.return_value = {
            "messages": [{"id": "msg_1"}],
        }

        result = gmail_service.get_email_detail(user_id, "msg_1")
        assert result["sender"] == "john@example.com"

    def test_missing_from_header(self, gmail_service, mock_gmail_api, user_id):
        """Missing From header defaults to empty string."""
        msg = _make_message("msg_1")
        # Remove From header
        msg["payload"]["headers"] = [
            h for h in msg["payload"]["headers"] if h["name"] != "From"
        ]
        mock_gmail_api.users().messages().get().execute.return_value = msg
        mock_gmail_api.users().threads().get().execute.return_value = {
            "messages": [{"id": "msg_1"}],
        }

        result = gmail_service.get_email_detail(user_id, "msg_1")
        assert result["sender"] == ""
