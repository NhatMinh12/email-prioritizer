"""Claude AI service for email classification."""

import json
import logging
from typing import Optional

import anthropic

from app.config import settings
from app.models.email import Email
from app.models.user import UserPreference
from app.schemas.claude import BatchClassificationResponse, SingleEmailClassification

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 10


def _build_system_prompt(preferences: Optional[UserPreference]) -> list[dict]:
    """Build the system prompt with optional prompt caching for preferences.

    Returns a list of content blocks for the system parameter.
    The preferences block uses cache_control for prompt caching when present.
    """
    base = (
        "You are an email priority classifier. Analyze each email and classify it.\n\n"
        "For each email, determine:\n"
        "- priority: 'high', 'medium', or 'low'\n"
        "- urgency: 'urgent', 'time_sensitive', 'normal', or 'low'\n"
        "- needs_response: true or false\n"
        "- reason: brief explanation (1-2 sentences)\n"
        "- action_items: list of specific actions needed (or null if none)\n\n"
        "Return ONLY valid JSON matching this exact structure:\n"
        '{"classifications": [{"email_index": 0, "priority": "...", "urgency": "...", '
        '"needs_response": true/false, "reason": "...", "action_items": [...] or null}, ...]}\n\n'
        "Rules:\n"
        "- email_index must match the 0-based position of the email in the list\n"
        "- Return one classification per email, in order\n"
        "- Do NOT include any text outside the JSON object\n"
    )

    blocks = [{"type": "text", "text": base}]

    if preferences:
        pref_lines = ["\nUser preferences:"]
        if preferences.important_senders:
            pref_lines.append(
                f"- Important senders (prioritize higher): {preferences.important_senders}"
            )
        if preferences.important_keywords:
            pref_lines.append(
                f"- Important keywords (prioritize higher): {preferences.important_keywords}"
            )
        if preferences.response_rate is not None:
            pref_lines.append(
                f"- User's typical response rate: {preferences.response_rate:.0%}"
            )
        pref_text = "\n".join(pref_lines)
        blocks.append({
            "type": "text",
            "text": pref_text,
            "cache_control": {"type": "ephemeral"},
        })

    return blocks


def _build_user_message(emails: list[Email]) -> str:
    """Format emails into the user message for Claude."""
    parts = []
    for i, email in enumerate(emails):
        parts.append(
            f"--- Email {i} ---\n"
            f"From: {email.sender}\n"
            f"Subject: {email.subject}\n"
            f"Preview: {email.body_preview or '(no preview)'}\n"
            f"Has attachments: {email.has_attachments}\n"
            f"Thread length: {email.thread_length}\n"
        )
    return "\n".join(parts)


def _parse_response(response_text: str, expected_count: int) -> BatchClassificationResponse:
    """Parse and validate Claude's JSON response.

    Raises ValueError if the response cannot be parsed or validated.
    """
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        if lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
        else:
            text = "\n".join(lines[1:]).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned invalid JSON: {exc}") from exc

    result = BatchClassificationResponse.model_validate(data)

    if len(result.classifications) != expected_count:
        logger.warning(
            "Expected %d classifications, got %d",
            expected_count,
            len(result.classifications),
        )

    return result


class ClaudeService:
    """Wrapper around the Anthropic API for email classification."""

    def __init__(self, client: anthropic.Anthropic) -> None:
        self._client = client

    def classify_batch(
        self,
        emails: list[Email],
        preferences: Optional[UserPreference] = None,
    ) -> list[SingleEmailClassification]:
        """Classify a batch of emails (up to MAX_BATCH_SIZE).

        Args:
            emails: List of Email models to classify (max 10).
            preferences: User preferences for context.

        Returns:
            List of SingleEmailClassification results.

        Raises:
            ValueError: If batch exceeds MAX_BATCH_SIZE or response is unparseable.
            anthropic.APIError: On API failures (timeout, rate limit, etc.)
        """
        if not emails:
            return []

        if len(emails) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size {len(emails)} exceeds maximum {MAX_BATCH_SIZE}"
            )

        system_prompt = _build_system_prompt(preferences)
        user_message = _build_user_message(emails)

        logger.info("Classifying batch of %d emails via Claude", len(emails))

        message = self._client.messages.create(
            model=settings.classification_model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.0,
        )

        response_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                response_text += block.text

        result = _parse_response(response_text, expected_count=len(emails))
        return result.classifications
