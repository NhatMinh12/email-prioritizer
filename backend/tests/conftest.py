"""Shared test fixtures."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import anthropic
import fakeredis
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
from app.services.cache_service import CacheService
from app.services.classifier import EmailClassifier
from app.services.claude_service import ClaudeService

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


# --- Service-layer fixtures ---


@pytest.fixture()
def fake_redis_client():
    """In-memory Redis for testing."""
    return fakeredis.FakeRedis()


@pytest.fixture()
def cache_service(fake_redis_client):
    """CacheService backed by fakeredis."""
    return CacheService(redis_client=fake_redis_client)


@pytest.fixture()
def mock_anthropic_client():
    """Mock Anthropic client."""
    return MagicMock(spec=anthropic.Anthropic)


@pytest.fixture()
def claude_service(mock_anthropic_client):
    """ClaudeService with a mocked Anthropic client."""
    return ClaudeService(client=mock_anthropic_client)


@pytest.fixture()
def mock_claude_service():
    """Fully mocked ClaudeService for classifier tests."""
    return MagicMock(spec=ClaudeService)


@pytest.fixture()
def mock_cache_service():
    """Fully mocked CacheService for classifier tests."""
    mock = MagicMock(spec=CacheService)
    # Default: cache miss
    mock.get.return_value = None
    return mock


@pytest.fixture()
def classifier(db_session, mock_claude_service, mock_cache_service):
    """EmailClassifier with mocked dependencies."""
    return EmailClassifier(
        db_session=db_session,
        claude_service=mock_claude_service,
        cache_service=mock_cache_service,
    )


@pytest.fixture()
def email_factory(db_session, sample_user):
    """Factory to create multiple test emails."""

    def _create(count=1, **overrides):
        emails = []
        for i in range(count):
            email = Email(
                user_id=sample_user.id,
                gmail_id=overrides.get("gmail_id", f"msg_{uuid.uuid4().hex[:8]}"),
                sender=overrides.get("sender", f"sender{i}@example.com"),
                subject=overrides.get("subject", f"Test Subject {i}"),
                body_preview=overrides.get("body_preview", f"Preview {i}"),
                received_at=overrides.get(
                    "received_at", datetime.now(timezone.utc)
                ),
                has_attachments=overrides.get("has_attachments", False),
                thread_length=overrides.get("thread_length", 1),
            )
            db_session.add(email)
            emails.append(email)
        db_session.flush()
        return emails

    return _create
