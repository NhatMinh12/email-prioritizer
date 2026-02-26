"""Tests for Pydantic schemas."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models import PriorityLevel, UrgencyLevel
from app.schemas.classification import ClassificationFeedback, ClassificationResponse
from app.schemas.email import EmailCreate, EmailListResponse, EmailResponse
from app.schemas.user import (
    UserCreate,
    UserPreferenceResponse,
    UserPreferenceUpdate,
    UserResponse,
)


class TestUserSchemas:
    """Tests for user-related schemas."""

    def test_user_create_valid(self):
        """Test creating a user with valid email."""
        user = UserCreate(email="test@example.com")
        assert user.email == "test@example.com"

    def test_user_create_invalid_email(self):
        """Test that invalid email is rejected."""
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email")

    def test_user_response_from_attributes(self):
        """Test UserResponse can be created from ORM-like attributes."""

        class FakeUser:
            id = uuid.uuid4()
            email = "test@example.com"
            created_at = datetime.now(timezone.utc)
            updated_at = datetime.now(timezone.utc)

        response = UserResponse.model_validate(FakeUser(), from_attributes=True)
        assert response.email == "test@example.com"

    def test_user_preference_update_partial(self):
        """Test that preference update allows partial updates."""
        update = UserPreferenceUpdate(important_senders=["vip@test.com"])
        assert update.important_senders == ["vip@test.com"]
        assert update.important_keywords is None
        assert update.response_rate is None

    def test_user_preference_response(self):
        """Test UserPreferenceResponse schema."""

        class FakePref:
            user_id = uuid.uuid4()
            important_senders = ["boss@company.com"]
            important_keywords = ["urgent"]
            response_rate = 0.9
            updated_at = datetime.now(timezone.utc)

        response = UserPreferenceResponse.model_validate(FakePref(), from_attributes=True)
        assert response.important_senders == ["boss@company.com"]
        assert response.response_rate == 0.9


class TestEmailSchemas:
    """Tests for email-related schemas."""

    def test_email_create_valid(self):
        """Test creating an email with all fields."""
        email = EmailCreate(
            gmail_id="msg_123",
            sender="sender@example.com",
            subject="Test Subject",
            body_preview="Preview text...",
            received_at=datetime.now(timezone.utc),
            has_attachments=True,
            thread_length=3,
        )
        assert email.gmail_id == "msg_123"
        assert email.has_attachments is True
        assert email.thread_length == 3

    def test_email_create_defaults(self):
        """Test EmailCreate defaults for optional fields."""
        email = EmailCreate(
            gmail_id="msg_123",
            sender="sender@example.com",
            subject="Test",
            received_at=datetime.now(timezone.utc),
        )
        assert email.body_preview is None
        assert email.has_attachments is False
        assert email.thread_length == 1

    def test_email_create_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            EmailCreate(gmail_id="msg_123")  # missing sender, subject, received_at

    def test_email_response_with_classification(self):
        """Test EmailResponse includes nested classification."""

        class FakeClassification:
            id = uuid.uuid4()
            email_id = uuid.uuid4()
            priority = PriorityLevel.HIGH
            urgency = UrgencyLevel.URGENT
            needs_response = True
            reason = "Important email"
            action_items = ["Reply"]
            classified_at = datetime.now(timezone.utc)
            feedback = None

        class FakeEmail:
            id = uuid.uuid4()
            user_id = uuid.uuid4()
            gmail_id = "msg_456"
            sender = "vip@example.com"
            subject = "Urgent Request"
            body_preview = "Please review..."
            received_at = datetime.now(timezone.utc)
            has_attachments = False
            thread_length = 1
            classification = FakeClassification()

        response = EmailResponse.model_validate(FakeEmail(), from_attributes=True)
        assert response.classification is not None
        assert response.classification.priority == PriorityLevel.HIGH
        assert response.classification.urgency == UrgencyLevel.URGENT

    def test_email_response_without_classification(self):
        """Test EmailResponse with no classification."""

        class FakeEmail:
            id = uuid.uuid4()
            user_id = uuid.uuid4()
            gmail_id = "msg_789"
            sender = "sender@example.com"
            subject = "Normal Email"
            body_preview = None
            received_at = datetime.now(timezone.utc)
            has_attachments = False
            thread_length = 1
            classification = None

        response = EmailResponse.model_validate(FakeEmail(), from_attributes=True)
        assert response.classification is None

    def test_email_list_response(self):
        """Test EmailListResponse pagination fields."""
        response = EmailListResponse(
            emails=[],
            total=0,
            page=1,
            page_size=20,
        )
        assert response.total == 0
        assert response.page == 1


class TestClassificationSchemas:
    """Tests for classification-related schemas."""

    def test_classification_response(self):
        """Test ClassificationResponse with all fields."""

        class FakeClassification:
            id = uuid.uuid4()
            email_id = uuid.uuid4()
            priority = PriorityLevel.MEDIUM
            urgency = UrgencyLevel.TIME_SENSITIVE
            needs_response = False
            reason = "Newsletter from subscribed list"
            action_items = None
            classified_at = datetime.now(timezone.utc)
            feedback = "correct"

        response = ClassificationResponse.model_validate(
            FakeClassification(), from_attributes=True
        )
        assert response.priority == PriorityLevel.MEDIUM
        assert response.urgency == UrgencyLevel.TIME_SENSITIVE
        assert response.feedback == "correct"

    def test_classification_feedback_valid_values(self):
        """Test that valid feedback values are accepted."""
        for value in ["correct", "incorrect", "adjusted"]:
            feedback = ClassificationFeedback(feedback=value)
            assert feedback.feedback == value

    def test_classification_feedback_invalid_value(self):
        """Test that invalid feedback values are rejected."""
        with pytest.raises(ValidationError):
            ClassificationFeedback(feedback="maybe")

    def test_classification_feedback_empty_string(self):
        """Test that empty feedback is rejected."""
        with pytest.raises(ValidationError):
            ClassificationFeedback(feedback="")
