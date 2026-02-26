"""Tests for database models."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Classification,
    Email,
    PriorityLevel,
    UrgencyLevel,
    User,
    UserPreference,
)


class TestUserModel:
    """Tests for the User model."""

    def test_create_user(self, db_session: Session, sample_user: User):
        """Test creating a basic user."""
        fetched = db_session.get(User, sample_user.id)
        assert fetched is not None
        assert fetched.email == "test@example.com"
        assert fetched.oauth_token == "test_oauth_token"
        assert fetched.created_at is not None
        assert fetched.updated_at is not None

    def test_user_email_unique_constraint(self, db_session: Session, sample_user: User):
        """Test that duplicate emails are rejected."""
        duplicate = User(
            id=uuid.uuid4(),
            email="test@example.com",  # same email
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_user_repr(self, sample_user: User):
        """Test User string representation."""
        assert repr(sample_user) == "<User test@example.com>"

    def test_user_without_oauth_token(self, db_session: Session):
        """Test creating a user without an oauth token."""
        user = User(id=uuid.uuid4(), email="notoken@example.com")
        db_session.add(user)
        db_session.flush()
        fetched = db_session.get(User, user.id)
        assert fetched.oauth_token is None


class TestUserPreferenceModel:
    """Tests for the UserPreference model."""

    def test_create_preference(
        self, db_session: Session, sample_user_preference: UserPreference
    ):
        """Test creating user preferences."""
        fetched = db_session.get(UserPreference, sample_user_preference.user_id)
        assert fetched is not None
        assert fetched.important_senders == ["boss@company.com", "cto@company.com"]
        assert fetched.important_keywords == ["urgent", "deadline", "asap"]
        assert fetched.response_rate == 0.85

    def test_preference_jsonb_roundtrip(
        self, db_session: Session, sample_user: User
    ):
        """Test JSONB columns store and return data correctly."""
        pref = UserPreference(
            user_id=sample_user.id,
            important_senders=[{"email": "vip@test.com", "weight": 1.0}],
            important_keywords=["deadline", "budget"],
        )
        db_session.add(pref)
        db_session.flush()

        fetched = db_session.get(UserPreference, sample_user.id)
        assert fetched.important_senders == [{"email": "vip@test.com", "weight": 1.0}]
        assert fetched.important_keywords == ["deadline", "budget"]

    def test_preference_user_relationship(
        self,
        db_session: Session,
        sample_user: User,
        sample_user_preference: UserPreference,
    ):
        """Test the bidirectional relationship between User and UserPreference."""
        assert sample_user.preferences is not None
        assert sample_user.preferences.user_id == sample_user.id
        assert sample_user_preference.user.email == "test@example.com"


class TestEmailModel:
    """Tests for the Email model."""

    def test_create_email(self, db_session: Session, sample_email: Email):
        """Test creating a basic email."""
        fetched = db_session.get(Email, sample_email.id)
        assert fetched is not None
        assert fetched.gmail_id == "msg_abc123"
        assert fetched.sender == "sender@example.com"
        assert fetched.subject == "Test Email Subject"
        assert fetched.has_attachments is False
        assert fetched.thread_length == 1

    def test_email_gmail_id_unique_per_user(
        self, db_session: Session, sample_user: User, sample_email: Email
    ):
        """Test that (user_id, gmail_id) unique constraint prevents duplicates."""
        duplicate = Email(
            id=uuid.uuid4(),
            user_id=sample_user.id,
            gmail_id="msg_abc123",  # same gmail_id for same user
            sender="other@example.com",
            subject="Duplicate",
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_same_gmail_id_different_users(self, db_session: Session):
        """Test that the same gmail_id is allowed for different users."""
        user1 = User(id=uuid.uuid4(), email="user1@example.com")
        user2 = User(id=uuid.uuid4(), email="user2@example.com")
        db_session.add_all([user1, user2])
        db_session.flush()

        email1 = Email(
            id=uuid.uuid4(),
            user_id=user1.id,
            gmail_id="shared_msg_id",
            sender="sender@example.com",
            subject="Email 1",
            received_at=datetime.now(timezone.utc),
        )
        email2 = Email(
            id=uuid.uuid4(),
            user_id=user2.id,
            gmail_id="shared_msg_id",
            sender="sender@example.com",
            subject="Email 2",
            received_at=datetime.now(timezone.utc),
        )
        db_session.add_all([email1, email2])
        db_session.flush()  # Should not raise

    def test_email_user_relationship(
        self, db_session: Session, sample_user: User, sample_email: Email
    ):
        """Test the User -> Emails relationship."""
        assert len(sample_user.emails) == 1
        assert sample_user.emails[0].gmail_id == "msg_abc123"
        assert sample_email.user.email == "test@example.com"

    def test_email_repr(self, sample_email: Email):
        """Test Email string representation."""
        assert "msg_abc123" in repr(sample_email)


class TestClassificationModel:
    """Tests for the Classification model."""

    def test_create_classification(
        self, db_session: Session, sample_classification: Classification
    ):
        """Test creating a classification."""
        fetched = db_session.get(Classification, sample_classification.id)
        assert fetched is not None
        assert fetched.priority == PriorityLevel.HIGH
        assert fetched.urgency == UrgencyLevel.URGENT
        assert fetched.needs_response is True
        assert fetched.action_items == ["Reply by EOD", "Schedule follow-up meeting"]
        assert fetched.feedback is None
        assert fetched.classified_at is not None

    def test_classification_email_unique(
        self, db_session: Session, sample_email: Email, sample_classification: Classification
    ):
        """Test that only one classification per email is allowed."""
        duplicate = Classification(
            id=uuid.uuid4(),
            email_id=sample_email.id,
            priority=PriorityLevel.LOW,
            urgency=UrgencyLevel.NORMAL,
            needs_response=False,
            reason="Duplicate classification",
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_classification_email_relationship(
        self,
        db_session: Session,
        sample_email: Email,
        sample_classification: Classification,
    ):
        """Test the Email <-> Classification relationship."""
        assert sample_email.classification is not None
        assert sample_email.classification.priority == PriorityLevel.HIGH
        assert sample_classification.email.gmail_id == "msg_abc123"

    def test_classification_with_feedback(
        self, db_session: Session, sample_classification: Classification
    ):
        """Test updating classification with feedback."""
        sample_classification.feedback = "correct"
        db_session.flush()
        fetched = db_session.get(Classification, sample_classification.id)
        assert fetched.feedback == "correct"

    def test_classification_action_items_jsonb(
        self, db_session: Session, sample_email: Email
    ):
        """Test JSONB action_items with complex data."""
        # First remove the existing classification from sample_classification fixture
        # by creating a fresh email
        user = sample_email.user
        email = Email(
            id=uuid.uuid4(),
            user_id=user.id,
            gmail_id="msg_jsonb_test",
            sender="test@test.com",
            subject="JSONB Test",
            received_at=datetime.now(timezone.utc),
        )
        db_session.add(email)
        db_session.flush()

        classification = Classification(
            id=uuid.uuid4(),
            email_id=email.id,
            priority=PriorityLevel.MEDIUM,
            urgency=UrgencyLevel.TIME_SENSITIVE,
            needs_response=True,
            reason="Complex action items test",
            action_items=[
                {"task": "Review document", "deadline": "2026-03-01"},
                {"task": "Send feedback", "deadline": "2026-03-02"},
            ],
        )
        db_session.add(classification)
        db_session.flush()

        fetched = db_session.get(Classification, classification.id)
        assert len(fetched.action_items) == 2
        assert fetched.action_items[0]["task"] == "Review document"


class TestCascadeDelete:
    """Tests for cascade delete behavior."""

    def test_delete_user_cascades_to_emails(
        self, db_session: Session, sample_user: User, sample_email: Email
    ):
        """Test that deleting a user cascades to their emails."""
        email_id = sample_email.id
        db_session.delete(sample_user)
        db_session.flush()
        assert db_session.get(Email, email_id) is None

    def test_delete_user_cascades_to_preferences(
        self,
        db_session: Session,
        sample_user: User,
        sample_user_preference: UserPreference,
    ):
        """Test that deleting a user cascades to their preferences."""
        user_id = sample_user.id
        db_session.delete(sample_user)
        db_session.flush()
        assert db_session.get(UserPreference, user_id) is None

    def test_delete_user_cascades_to_classifications(
        self,
        db_session: Session,
        sample_user: User,
        sample_email: Email,
        sample_classification: Classification,
    ):
        """Test that deleting a user cascades through emails to classifications."""
        classification_id = sample_classification.id
        db_session.delete(sample_user)
        db_session.flush()
        assert db_session.get(Classification, classification_id) is None

    def test_delete_email_cascades_to_classification(
        self,
        db_session: Session,
        sample_email: Email,
        sample_classification: Classification,
    ):
        """Test that deleting an email cascades to its classification."""
        classification_id = sample_classification.id
        db_session.delete(sample_email)
        db_session.flush()
        assert db_session.get(Classification, classification_id) is None
