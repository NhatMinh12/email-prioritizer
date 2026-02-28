"""Email classification orchestrator.

Coordinates cache lookups, Claude API calls, rule-based fallback,
and database persistence.
"""

import logging
import re
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.base import PriorityLevel, UrgencyLevel
from app.models.classification import Classification
from app.models.email import Email
from app.models.user import UserPreference
from app.schemas.claude import SingleEmailClassification
from app.services.cache_service import CacheService
from app.services.claude_service import ClaudeService, MAX_BATCH_SIZE

logger = logging.getLogger(__name__)

NEWSLETTER_PATTERNS = [
    re.compile(r"noreply@", re.IGNORECASE),
    re.compile(r"no-reply@", re.IGNORECASE),
    re.compile(r"newsletter@", re.IGNORECASE),
    re.compile(r"marketing@", re.IGNORECASE),
    re.compile(r"notifications@", re.IGNORECASE),
]


def _is_newsletter(email: Email) -> bool:
    """Check if an email appears to be a newsletter or automated message."""
    for pattern in NEWSLETTER_PATTERNS:
        if pattern.search(email.sender):
            return True
    if email.body_preview and re.search(
        r"unsubscribe", email.body_preview, re.IGNORECASE
    ):
        return True
    return False


def _rule_based_classify(
    email: Email,
    preferences: Optional[UserPreference],
) -> SingleEmailClassification:
    """Fallback rule-based classification when Claude is unavailable.

    Heuristics:
    - Newsletter patterns -> LOW
    - Important sender match -> HIGH
    - Important keyword match -> boost priority
    - Default -> MEDIUM
    """
    if _is_newsletter(email):
        return SingleEmailClassification(
            email_index=0,
            priority=PriorityLevel.LOW,
            urgency=UrgencyLevel.LOW,
            needs_response=False,
            reason="Automated/newsletter email detected",
            action_items=None,
        )

    priority = PriorityLevel.MEDIUM
    urgency = UrgencyLevel.NORMAL
    needs_response = False
    reason = "Classified by rule-based fallback"

    if preferences:
        sender_lower = email.sender.lower()
        for important_sender in preferences.important_senders:
            if isinstance(important_sender, str) and important_sender.lower() in sender_lower:
                priority = PriorityLevel.HIGH
                urgency = UrgencyLevel.TIME_SENSITIVE
                needs_response = True
                reason = f"Email from important sender: {important_sender}"
                break

        searchable = f"{email.subject} {email.body_preview or ''}".lower()
        matched_keywords = [
            kw
            for kw in preferences.important_keywords
            if isinstance(kw, str) and kw.lower() in searchable
        ]

        if matched_keywords:
            if priority != PriorityLevel.HIGH:
                priority = (
                    PriorityLevel.HIGH
                    if len(matched_keywords) >= 2
                    else PriorityLevel.MEDIUM
                )
                urgency = (
                    UrgencyLevel.TIME_SENSITIVE
                    if len(matched_keywords) >= 2
                    else UrgencyLevel.NORMAL
                )
            reason = f"Contains important keywords: {', '.join(matched_keywords)}"
            needs_response = True

    return SingleEmailClassification(
        email_index=0,
        priority=priority,
        urgency=urgency,
        needs_response=needs_response,
        reason=reason,
        action_items=None,
    )


def _classification_to_cache_dict(c: SingleEmailClassification) -> dict:
    """Convert a classification result to a dict suitable for caching."""
    return {
        "priority": c.priority.value,
        "urgency": c.urgency.value,
        "needs_response": c.needs_response,
        "reason": c.reason,
        "action_items": c.action_items,
    }


def _cache_dict_to_classification(
    data: dict, email_index: int = 0
) -> SingleEmailClassification:
    """Reconstruct a SingleEmailClassification from a cached dict."""
    return SingleEmailClassification(
        email_index=email_index,
        priority=PriorityLevel(data["priority"]),
        urgency=UrgencyLevel(data["urgency"]),
        needs_response=data["needs_response"],
        reason=data["reason"],
        action_items=data.get("action_items"),
    )


class EmailClassifier:
    """Orchestrates the full email classification pipeline.

    Flow:
    1. Skip already-classified emails
    2. Pre-filter newsletters -> auto LOW
    3. Check Redis cache for each email
    4. Batch remaining emails for Claude API
    5. On Claude failure -> rule-based fallback
    6. Persist Classification records to DB
    7. Cache results in Redis
    """

    def __init__(
        self,
        db_session: Session,
        claude_service: ClaudeService,
        cache_service: CacheService,
    ) -> None:
        self._db = db_session
        self._claude = claude_service
        self._cache = cache_service

    def classify_emails(
        self,
        emails: list[Email],
        preferences: Optional[UserPreference] = None,
    ) -> list[Classification]:
        """Classify a list of emails and persist results.

        Args:
            emails: Email models to classify. Must already be persisted in DB.
            preferences: User preferences for classification context.

        Returns:
            List of Classification ORM models (persisted via flush, not commit).
        """
        if not emails:
            return []

        results: dict[uuid.UUID, SingleEmailClassification] = {}
        uncached_emails: list[Email] = []

        for email in emails:
            # Skip already classified
            if email.classification is not None:
                continue

            # Pre-filter newsletters
            if _is_newsletter(email):
                results[email.id] = SingleEmailClassification(
                    email_index=0,
                    priority=PriorityLevel.LOW,
                    urgency=UrgencyLevel.LOW,
                    needs_response=False,
                    reason="Automated/newsletter email detected",
                    action_items=None,
                )
                continue

            # Cache check
            cache_key = CacheService.make_cache_key(
                email.user_id, email.sender, email.subject, email.body_preview
            )
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for email %s", email.id)
                results[email.id] = _cache_dict_to_classification(cached)
                continue

            uncached_emails.append(email)

        # Batch classify via Claude
        if uncached_emails:
            claude_results = self._classify_via_claude(uncached_emails, preferences)
            results.update(claude_results)

        # Persist and cache
        classifications = []
        for email in emails:
            if email.classification is not None:
                classifications.append(email.classification)
                continue

            result = results.get(email.id)
            if result is None:
                logger.error(
                    "No classification result for email %s, applying fallback",
                    email.id,
                )
                result = _rule_based_classify(email, preferences)

            classification = Classification(
                email_id=email.id,
                priority=result.priority,
                urgency=result.urgency,
                needs_response=result.needs_response,
                reason=result.reason,
                action_items=result.action_items,
            )
            self._db.add(classification)
            classifications.append(classification)

            # Cache the result
            cache_key = CacheService.make_cache_key(
                email.user_id, email.sender, email.subject, email.body_preview
            )
            self._cache.set(cache_key, _classification_to_cache_dict(result))

        self._db.flush()
        return classifications

    def _classify_via_claude(
        self,
        emails: list[Email],
        preferences: Optional[UserPreference],
    ) -> dict[uuid.UUID, SingleEmailClassification]:
        """Send emails to Claude in batches, with rule-based fallback on failure."""
        results: dict[uuid.UUID, SingleEmailClassification] = {}

        for batch_start in range(0, len(emails), MAX_BATCH_SIZE):
            batch = emails[batch_start : batch_start + MAX_BATCH_SIZE]

            try:
                claude_results = self._claude.classify_batch(batch, preferences)

                for classification in claude_results:
                    idx = classification.email_index
                    if 0 <= idx < len(batch):
                        results[batch[idx].id] = classification
                    else:
                        logger.warning(
                            "Claude returned invalid email_index %d for batch size %d",
                            idx,
                            len(batch),
                        )

                # Fallback for any emails Claude missed
                for i, email in enumerate(batch):
                    if email.id not in results:
                        logger.warning(
                            "Claude did not classify email %s (index %d), "
                            "applying fallback",
                            email.id,
                            i,
                        )
                        results[email.id] = _rule_based_classify(email, preferences)

            except Exception as exc:
                logger.error(
                    "Claude API failed for batch of %d emails: %s. "
                    "Applying rule-based fallback.",
                    len(batch),
                    exc,
                )
                for email in batch:
                    results[email.id] = _rule_based_classify(email, preferences)

        return results
