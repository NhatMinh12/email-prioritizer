"""Tests for the email classification orchestrator."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models.base import PriorityLevel, UrgencyLevel
from app.models.classification import Classification
from app.models.email import Email
from app.models.user import UserPreference
from app.schemas.claude import SingleEmailClassification
from app.services.cache_service import CacheService
from app.services.classifier import (
    EmailClassifier,
    _cache_dict_to_classification,
    _classification_to_cache_dict,
    _is_newsletter,
    _rule_based_classify,
)


def _make_db_email(db_session: Session, user_id: uuid.UUID, **overrides) -> Email:
    """Create and flush an Email in the test DB."""
    email = Email(
        user_id=user_id,
        gmail_id=overrides.get("gmail_id", f"msg_{uuid.uuid4().hex[:8]}"),
        sender=overrides.get("sender", "sender@example.com"),
        subject=overrides.get("subject", "Test Subject"),
        body_preview=overrides.get("body_preview", "Test preview"),
        received_at=overrides.get("received_at", datetime.now(timezone.utc)),
        has_attachments=overrides.get("has_attachments", False),
        thread_length=overrides.get("thread_length", 1),
    )
    db_session.add(email)
    db_session.flush()
    return email


def _make_classification_result(**overrides) -> SingleEmailClassification:
    """Create a SingleEmailClassification for testing."""
    return SingleEmailClassification(
        email_index=overrides.get("email_index", 0),
        priority=overrides.get("priority", PriorityLevel.MEDIUM),
        urgency=overrides.get("urgency", UrgencyLevel.NORMAL),
        needs_response=overrides.get("needs_response", False),
        reason=overrides.get("reason", "Test reason"),
        action_items=overrides.get("action_items", None),
    )


class TestIsNewsletter:
    """Tests for newsletter detection."""

    def test_noreply_sender_detected(self):
        email = MagicMock(spec=Email)
        email.sender = "noreply@company.com"
        email.body_preview = "Hello"
        assert _is_newsletter(email) is True

    def test_no_reply_sender_detected(self):
        email = MagicMock(spec=Email)
        email.sender = "no-reply@company.com"
        email.body_preview = "Hello"
        assert _is_newsletter(email) is True

    def test_newsletter_sender_detected(self):
        email = MagicMock(spec=Email)
        email.sender = "newsletter@company.com"
        email.body_preview = "Hello"
        assert _is_newsletter(email) is True

    def test_marketing_sender_detected(self):
        email = MagicMock(spec=Email)
        email.sender = "marketing@company.com"
        email.body_preview = "Hello"
        assert _is_newsletter(email) is True

    def test_unsubscribe_in_body_detected(self):
        email = MagicMock(spec=Email)
        email.sender = "realuser@company.com"
        email.body_preview = "Click here to unsubscribe from this list"
        assert _is_newsletter(email) is True

    def test_normal_email_not_newsletter(self):
        email = MagicMock(spec=Email)
        email.sender = "colleague@company.com"
        email.body_preview = "Can we meet tomorrow?"
        assert _is_newsletter(email) is False

    def test_none_body_preview_handled(self):
        email = MagicMock(spec=Email)
        email.sender = "someone@company.com"
        email.body_preview = None
        assert _is_newsletter(email) is False


class TestRuleBasedClassify:
    """Tests for fallback rule-based classification."""

    def test_newsletter_returns_low(self):
        email = MagicMock(spec=Email)
        email.sender = "noreply@company.com"
        email.body_preview = "Weekly digest"
        email.subject = "Newsletter"
        result = _rule_based_classify(email, None)
        assert result.priority == PriorityLevel.LOW
        assert result.urgency == UrgencyLevel.LOW
        assert result.needs_response is False

    def test_important_sender_returns_high(self):
        email = MagicMock(spec=Email)
        email.sender = "boss@company.com"
        email.body_preview = "Please review"
        email.subject = "Review Request"
        pref = MagicMock(spec=UserPreference)
        pref.important_senders = ["boss@company.com"]
        pref.important_keywords = []
        result = _rule_based_classify(email, pref)
        assert result.priority == PriorityLevel.HIGH
        assert result.urgency == UrgencyLevel.TIME_SENSITIVE
        assert result.needs_response is True

    def test_single_keyword_returns_medium(self):
        email = MagicMock(spec=Email)
        email.sender = "someone@company.com"
        email.body_preview = "This is urgent"
        email.subject = "Question"
        pref = MagicMock(spec=UserPreference)
        pref.important_senders = []
        pref.important_keywords = ["urgent"]
        result = _rule_based_classify(email, pref)
        assert result.priority == PriorityLevel.MEDIUM
        assert result.needs_response is True

    def test_multiple_keywords_returns_high(self):
        email = MagicMock(spec=Email)
        email.sender = "someone@company.com"
        email.body_preview = "This is urgent, deadline tomorrow"
        email.subject = "Question"
        pref = MagicMock(spec=UserPreference)
        pref.important_senders = []
        pref.important_keywords = ["urgent", "deadline"]
        result = _rule_based_classify(email, pref)
        assert result.priority == PriorityLevel.HIGH
        assert result.urgency == UrgencyLevel.TIME_SENSITIVE

    def test_no_preferences_returns_medium(self):
        email = MagicMock(spec=Email)
        email.sender = "someone@company.com"
        email.body_preview = "Hello there"
        email.subject = "Hi"
        result = _rule_based_classify(email, None)
        assert result.priority == PriorityLevel.MEDIUM
        assert result.urgency == UrgencyLevel.NORMAL
        assert result.needs_response is False

    def test_no_match_returns_medium(self):
        email = MagicMock(spec=Email)
        email.sender = "random@other.com"
        email.body_preview = "Nothing special here"
        email.subject = "Stuff"
        pref = MagicMock(spec=UserPreference)
        pref.important_senders = ["boss@company.com"]
        pref.important_keywords = ["urgent"]
        result = _rule_based_classify(email, pref)
        assert result.priority == PriorityLevel.MEDIUM


class TestCacheRoundtrip:
    """Tests for classification <-> cache dict conversion."""

    def test_roundtrip_preserves_all_fields(self):
        original = _make_classification_result(
            priority=PriorityLevel.HIGH,
            urgency=UrgencyLevel.URGENT,
            needs_response=True,
            reason="Important email",
            action_items=["Reply", "Schedule meeting"],
        )
        cache_dict = _classification_to_cache_dict(original)
        restored = _cache_dict_to_classification(cache_dict)
        assert restored.priority == original.priority
        assert restored.urgency == original.urgency
        assert restored.needs_response == original.needs_response
        assert restored.reason == original.reason
        assert restored.action_items == original.action_items

    def test_roundtrip_with_null_action_items(self):
        original = _make_classification_result(action_items=None)
        cache_dict = _classification_to_cache_dict(original)
        restored = _cache_dict_to_classification(cache_dict)
        assert restored.action_items is None


class TestEmailClassifier:
    """Integration tests for the classification orchestrator."""

    def test_classify_empty_list_returns_empty(self, classifier):
        result = classifier.classify_emails([])
        assert result == []

    def test_classify_newsletter_skips_claude(
        self, classifier, mock_claude_service, db_session, sample_user
    ):
        email = _make_db_email(
            db_session, sample_user.id, sender="noreply@company.com"
        )
        result = classifier.classify_emails([email])
        assert len(result) == 1
        assert result[0].priority == PriorityLevel.LOW
        assert result[0].reason == "Automated/newsletter email detected"
        mock_claude_service.classify_batch.assert_not_called()

    def test_classify_cached_email_skips_claude(
        self, classifier, mock_claude_service, mock_cache_service,
        db_session, sample_user,
    ):
        email = _make_db_email(db_session, sample_user.id)
        mock_cache_service.get.return_value = {
            "priority": "high",
            "urgency": "urgent",
            "needs_response": True,
            "reason": "Cached result",
            "action_items": None,
        }
        result = classifier.classify_emails([email])
        assert len(result) == 1
        assert result[0].priority == PriorityLevel.HIGH
        assert result[0].reason == "Cached result"
        mock_claude_service.classify_batch.assert_not_called()

    def test_classify_uncached_calls_claude(
        self, classifier, mock_claude_service, db_session, sample_user
    ):
        email = _make_db_email(db_session, sample_user.id)
        mock_claude_service.classify_batch.return_value = [
            _make_classification_result(
                email_index=0,
                priority=PriorityLevel.HIGH,
                reason="Claude says important",
            )
        ]
        result = classifier.classify_emails([email])
        assert len(result) == 1
        assert result[0].priority == PriorityLevel.HIGH
        mock_claude_service.classify_batch.assert_called_once()

    def test_classify_already_classified_email_skipped(
        self, classifier, mock_claude_service, db_session, sample_user,
        sample_email, sample_classification,
    ):
        result = classifier.classify_emails([sample_email])
        assert len(result) == 1
        assert result[0] is sample_classification
        mock_claude_service.classify_batch.assert_not_called()

    def test_classify_persists_to_db(
        self, classifier, mock_claude_service, db_session, sample_user
    ):
        email = _make_db_email(db_session, sample_user.id)
        mock_claude_service.classify_batch.return_value = [
            _make_classification_result(email_index=0, priority=PriorityLevel.LOW)
        ]
        result = classifier.classify_emails([email])
        assert len(result) == 1
        # Verify it was flushed to the session (has an email_id)
        assert result[0].email_id == email.id
        # Verify we can query it
        classification = (
            db_session.query(Classification)
            .filter_by(email_id=email.id)
            .first()
        )
        assert classification is not None
        assert classification.priority == PriorityLevel.LOW

    def test_classify_caches_result(
        self, classifier, mock_claude_service, mock_cache_service,
        db_session, sample_user,
    ):
        email = _make_db_email(db_session, sample_user.id)
        mock_claude_service.classify_batch.return_value = [
            _make_classification_result(email_index=0, priority=PriorityLevel.MEDIUM)
        ]
        classifier.classify_emails([email])
        mock_cache_service.set.assert_called_once()
        cached_data = mock_cache_service.set.call_args[0][1]
        assert cached_data["priority"] == "medium"

    def test_classify_claude_failure_uses_fallback(
        self, classifier, mock_claude_service, db_session, sample_user
    ):
        email = _make_db_email(db_session, sample_user.id)
        mock_claude_service.classify_batch.side_effect = Exception("API down")
        result = classifier.classify_emails([email])
        assert len(result) == 1
        # Fallback gives MEDIUM for normal emails
        assert result[0].priority == PriorityLevel.MEDIUM
        assert "rule-based fallback" in result[0].reason

    def test_classify_partial_claude_failure(
        self, classifier, mock_claude_service, db_session, sample_user
    ):
        """Claude returns results for some emails but not all."""
        emails = [
            _make_db_email(db_session, sample_user.id, sender=f"s{i}@example.com")
            for i in range(3)
        ]
        # Claude only classifies index 0, skips 1 and 2
        mock_claude_service.classify_batch.return_value = [
            _make_classification_result(
                email_index=0, priority=PriorityLevel.HIGH, reason="Claude classified"
            )
        ]
        result = classifier.classify_emails(emails)
        assert len(result) == 3
        assert result[0].priority == PriorityLevel.HIGH
        # Others get fallback
        assert result[1].priority == PriorityLevel.MEDIUM
        assert result[2].priority == PriorityLevel.MEDIUM

    def test_classify_with_preferences(
        self, classifier, mock_claude_service, db_session,
        sample_user, sample_user_preference,
    ):
        email = _make_db_email(db_session, sample_user.id)
        mock_claude_service.classify_batch.return_value = [
            _make_classification_result(email_index=0)
        ]
        classifier.classify_emails([email], preferences=sample_user_preference)
        call_args = mock_claude_service.classify_batch.call_args
        assert call_args[1].get("preferences") is sample_user_preference or \
            call_args[0][1] is sample_user_preference

    def test_classify_mixed_cached_and_uncached(
        self, classifier, mock_claude_service, mock_cache_service,
        db_session, sample_user,
    ):
        email_cached = _make_db_email(
            db_session, sample_user.id, sender="cached@example.com"
        )
        email_uncached = _make_db_email(
            db_session, sample_user.id, sender="uncached@example.com"
        )

        # First call returns cached, second returns None
        mock_cache_service.get.side_effect = [
            {
                "priority": "low",
                "urgency": "low",
                "needs_response": False,
                "reason": "From cache",
                "action_items": None,
            },
            None,
        ]
        mock_claude_service.classify_batch.return_value = [
            _make_classification_result(
                email_index=0,
                priority=PriorityLevel.HIGH,
                reason="Claude classified",
            )
        ]

        result = classifier.classify_emails([email_cached, email_uncached])
        assert len(result) == 2
        assert result[0].priority == PriorityLevel.LOW  # from cache
        assert result[1].priority == PriorityLevel.HIGH  # from Claude

    def test_classify_batches_large_sets(
        self, classifier, mock_claude_service, db_session, sample_user
    ):
        """Emails exceeding MAX_BATCH_SIZE should be split into multiple batches."""
        emails = [
            _make_db_email(db_session, sample_user.id, sender=f"s{i}@example.com")
            for i in range(15)
        ]

        def mock_classify(batch, preferences=None):
            return [
                _make_classification_result(email_index=i, reason=f"Batch result {i}")
                for i in range(len(batch))
            ]

        mock_claude_service.classify_batch.side_effect = mock_classify
        result = classifier.classify_emails(emails)
        assert len(result) == 15
        # Should have been called twice: batch of 10 + batch of 5
        assert mock_claude_service.classify_batch.call_count == 2
