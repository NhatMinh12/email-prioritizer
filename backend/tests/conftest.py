"""Shared test fixtures."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import Base
from app.models import (
    Classification,
    Email,
    PriorityLevel,
    UrgencyLevel,
    User,
    UserPreference,
)

# Use the same database URL but with a test-specific database name approach:
# We use the main DB for tests but wrap each test in a transaction rollback.
TEST_DATABASE_URL = settings.database_url


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session(engine):
    """Per-test transactional session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def sample_user(db_session: Session) -> User:
    """Create a sample user for testing."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        oauth_token="test_oauth_token",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def sample_user_preference(db_session: Session, sample_user: User) -> UserPreference:
    """Create sample user preferences."""
    pref = UserPreference(
        user_id=sample_user.id,
        important_senders=["boss@company.com", "cto@company.com"],
        important_keywords=["urgent", "deadline", "asap"],
        response_rate=0.85,
    )
    db_session.add(pref)
    db_session.flush()
    return pref


@pytest.fixture()
def sample_email(db_session: Session, sample_user: User) -> Email:
    """Create a sample email for testing."""
    email = Email(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        gmail_id="msg_abc123",
        sender="sender@example.com",
        subject="Test Email Subject",
        body_preview="This is a test email body preview...",
        received_at=datetime.now(timezone.utc),
        has_attachments=False,
        thread_length=1,
    )
    db_session.add(email)
    db_session.flush()
    return email


@pytest.fixture()
def sample_classification(
    db_session: Session, sample_email: Email
) -> Classification:
    """Create a sample classification for testing."""
    classification = Classification(
        id=uuid.uuid4(),
        email_id=sample_email.id,
        priority=PriorityLevel.HIGH,
        urgency=UrgencyLevel.URGENT,
        needs_response=True,
        reason="Email from important sender with urgent keywords",
        action_items=["Reply by EOD", "Schedule follow-up meeting"],
    )
    db_session.add(classification)
    db_session.flush()
    return classification
