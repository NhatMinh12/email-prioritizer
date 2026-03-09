"""Tests for email API routes."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_cache_service, get_claude_service, get_gmail_service
from app.main import app
from app.models import Classification, Email, PriorityLevel, UrgencyLevel, User
from app.schemas.claude import SingleEmailClassification
from app.services.gmail_service import GmailService
from app.services.oauth_service import OAuthError


class TestListEmails:
    def test_list_emails_empty(
        self, authenticated_client: TestClient, sample_user: User
    ):
        response = authenticated_client.get("/api/emails")
        assert response.status_code == 200
        data = response.json()
        assert data["emails"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_emails_returns_emails(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
    ):
        response = authenticated_client.get("/api/emails")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["emails"]) == 1
        assert data["emails"][0]["gmail_id"] == sample_email.gmail_id

    def test_list_emails_with_classification(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
        sample_classification: Classification,
    ):
        response = authenticated_client.get("/api/emails")
        assert response.status_code == 200
        email_data = response.json()["emails"][0]
        assert email_data["classification"] is not None
        assert email_data["classification"]["priority"] == "high"

    def test_list_emails_pagination(
        self,
        authenticated_client: TestClient,
        email_factory,
    ):
        email_factory(count=5)
        response = authenticated_client.get(
            "/api/emails", params={"page": 1, "page_size": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["emails"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_list_emails_page_2(
        self,
        authenticated_client: TestClient,
        email_factory,
    ):
        email_factory(count=5)
        response = authenticated_client.get(
            "/api/emails", params={"page": 2, "page_size": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["emails"]) == 2

    def test_list_emails_filter_by_priority(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
        sample_classification: Classification,
        db_session,
        sample_user: User,
    ):
        # Create another email with LOW priority
        email2 = Email(
            user_id=sample_user.id,
            gmail_id="msg_low",
            sender="noreply@spam.com",
            subject="Newsletter",
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(email2)
        db_session.flush()
        Classification(
            email_id=email2.id,
            priority=PriorityLevel.LOW,
            urgency=UrgencyLevel.LOW,
            needs_response=False,
            reason="Test",
        )
        db_session.add(
            Classification(
                email_id=email2.id,
                priority=PriorityLevel.LOW,
                urgency=UrgencyLevel.LOW,
                needs_response=False,
                reason="Test",
            )
        )
        db_session.flush()

        response = authenticated_client.get(
            "/api/emails", params={"priority": "high"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["emails"][0]["classification"]["priority"] == "high"

    def test_list_emails_requires_auth(self, client: TestClient):
        response = client.get("/api/emails")
        assert response.status_code == 401


class TestGetEmail:
    def test_get_email_returns_email(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
    ):
        response = authenticated_client.get(f"/api/emails/{sample_email.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["gmail_id"] == sample_email.gmail_id
        assert data["subject"] == sample_email.subject

    def test_get_email_with_classification(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
        sample_classification: Classification,
    ):
        response = authenticated_client.get(f"/api/emails/{sample_email.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["classification"]["priority"] == "high"
        assert data["classification"]["urgency"] == "urgent"

    def test_get_email_not_found(
        self, authenticated_client: TestClient, sample_user: User
    ):
        fake_id = uuid.uuid4()
        response = authenticated_client.get(f"/api/emails/{fake_id}")
        assert response.status_code == 404

    def test_get_email_wrong_user(
        self,
        authenticated_client: TestClient,
        db_session,
    ):
        """Email exists but belongs to another user — should return 404."""
        other_user = User(email="other@example.com")
        db_session.add(other_user)
        db_session.flush()

        other_email = Email(
            user_id=other_user.id,
            gmail_id="msg_other",
            sender="s@s.com",
            subject="Other",
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(other_email)
        db_session.flush()

        response = authenticated_client.get(f"/api/emails/{other_email.id}")
        assert response.status_code == 404

    def test_get_email_requires_auth(self, client: TestClient):
        response = client.get(f"/api/emails/{uuid.uuid4()}")
        assert response.status_code == 401


class TestSyncEmails:
    def test_sync_empty_returns_zero(
        self, authenticated_client: TestClient, sample_user: User
    ):
        """Gmail service returns empty list → zero synced."""
        mock_gmail = MagicMock(spec=GmailService)
        mock_gmail.fetch_emails.return_value = []
        app.dependency_overrides[get_gmail_service] = lambda: mock_gmail

        response = authenticated_client.post("/api/emails/sync")
        assert response.status_code == 200
        assert response.json()["synced"] == 0

    def test_sync_with_mock_gmail_service(
        self,
        authenticated_client: TestClient,
        sample_user: User,
    ):
        """Override Gmail service to return emails."""
        mock_gmail = MagicMock(spec=GmailService)
        mock_gmail.fetch_emails.return_value = [
            {
                "gmail_id": "msg_synced_1",
                "sender": "s@s.com",
                "subject": "Synced Email",
                "body_preview": "Body",
                "received_at": datetime.now(timezone.utc).isoformat(),
                "has_attachments": False,
                "thread_length": 1,
            }
        ]
        app.dependency_overrides[get_gmail_service] = lambda: mock_gmail

        response = authenticated_client.post("/api/emails/sync")
        assert response.status_code == 200
        assert response.json()["synced"] == 1

    def test_sync_deduplicates_by_gmail_id(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
    ):
        """Already-existing gmail_id should not be re-added."""
        mock_gmail = MagicMock(spec=GmailService)
        mock_gmail.fetch_emails.return_value = [
            {
                "gmail_id": sample_email.gmail_id,  # Already exists
                "sender": "s@s.com",
                "subject": "Duplicate",
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        app.dependency_overrides[get_gmail_service] = lambda: mock_gmail

        response = authenticated_client.post("/api/emails/sync")
        assert response.status_code == 200
        assert response.json()["synced"] == 0

    def test_sync_oauth_error_returns_401(
        self, authenticated_client: TestClient, sample_user: User
    ):
        """OAuthError during sync returns 401."""
        mock_gmail = MagicMock(spec=GmailService)
        mock_gmail.fetch_emails.side_effect = OAuthError("Token revoked")
        app.dependency_overrides[get_gmail_service] = lambda: mock_gmail

        response = authenticated_client.post("/api/emails/sync")
        assert response.status_code == 401
        assert "re-authentication" in response.json()["detail"].lower()

    def test_sync_gmail_api_error_returns_502(
        self, authenticated_client: TestClient, sample_user: User
    ):
        """General Gmail API failure returns 502."""
        mock_gmail = MagicMock(spec=GmailService)
        mock_gmail.fetch_emails.side_effect = RuntimeError("API unavailable")
        app.dependency_overrides[get_gmail_service] = lambda: mock_gmail

        response = authenticated_client.post("/api/emails/sync")
        assert response.status_code == 502
        assert "Failed to fetch" in response.json()["detail"]

    def test_sync_requires_auth(self, client: TestClient):
        response = client.post("/api/emails/sync")
        assert response.status_code == 401


class TestClassifyEmails:
    def test_classify_no_unclassified_returns_zero(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
        sample_classification: Classification,
    ):
        response = authenticated_client.post("/api/emails/classify")
        assert response.status_code == 200
        assert response.json()["classified"] == 0

    def test_classify_no_emails_returns_zero(
        self,
        authenticated_client: TestClient,
        sample_user: User,
    ):
        response = authenticated_client.post("/api/emails/classify")
        assert response.status_code == 200
        assert response.json()["classified"] == 0

    def test_classify_with_specific_ids(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
        mock_claude_service,
        mock_cache_service,
    ):
        """Classify specific emails by ID."""
        mock_claude_service.classify_batch.return_value = [
            SingleEmailClassification(
                email_index=0,
                priority=PriorityLevel.MEDIUM,
                urgency=UrgencyLevel.NORMAL,
                needs_response=False,
                reason="Test classification",
            )
        ]
        app.dependency_overrides[get_claude_service] = lambda: mock_claude_service
        app.dependency_overrides[get_cache_service] = lambda: mock_cache_service

        response = authenticated_client.post(
            "/api/emails/classify",
            json=[str(sample_email.id)],
        )
        assert response.status_code == 200
        assert response.json()["classified"] == 1

        app.dependency_overrides.pop(get_claude_service, None)
        app.dependency_overrides.pop(get_cache_service, None)

    def test_classify_requires_auth(self, client: TestClient):
        response = client.post("/api/emails/classify")
        assert response.status_code == 401


class TestSubmitFeedback:
    def test_submit_valid_feedback(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
        sample_classification: Classification,
    ):
        response = authenticated_client.post(
            f"/api/emails/{sample_email.id}/feedback",
            json={"feedback": "correct"},
        )
        assert response.status_code == 200
        assert response.json()["feedback"] == "correct"

    def test_submit_incorrect_feedback(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
        sample_classification: Classification,
    ):
        response = authenticated_client.post(
            f"/api/emails/{sample_email.id}/feedback",
            json={"feedback": "incorrect"},
        )
        assert response.status_code == 200
        assert response.json()["feedback"] == "incorrect"

    def test_submit_adjusted_feedback(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
        sample_classification: Classification,
    ):
        response = authenticated_client.post(
            f"/api/emails/{sample_email.id}/feedback",
            json={"feedback": "adjusted"},
        )
        assert response.status_code == 200
        assert response.json()["feedback"] == "adjusted"

    def test_submit_invalid_feedback_value(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
        sample_classification: Classification,
    ):
        response = authenticated_client.post(
            f"/api/emails/{sample_email.id}/feedback",
            json={"feedback": "invalid_value"},
        )
        assert response.status_code == 422

    def test_feedback_email_not_found(
        self, authenticated_client: TestClient, sample_user: User
    ):
        response = authenticated_client.post(
            f"/api/emails/{uuid.uuid4()}/feedback",
            json={"feedback": "correct"},
        )
        assert response.status_code == 404

    def test_feedback_no_classification(
        self,
        authenticated_client: TestClient,
        sample_email: Email,
    ):
        """Email exists but has no classification yet."""
        response = authenticated_client.post(
            f"/api/emails/{sample_email.id}/feedback",
            json={"feedback": "correct"},
        )
        assert response.status_code == 404
        assert "No classification" in response.json()["detail"]

    def test_feedback_requires_auth(self, client: TestClient):
        response = client.post(
            f"/api/emails/{uuid.uuid4()}/feedback",
            json={"feedback": "correct"},
        )
        assert response.status_code == 401
