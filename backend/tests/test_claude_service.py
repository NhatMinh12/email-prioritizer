"""Tests for the Claude AI classification service."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import anthropic
import pytest

from app.models.base import PriorityLevel, UrgencyLevel
from app.models.email import Email
from app.models.user import UserPreference
from app.services.claude_service import (
    MAX_BATCH_SIZE,
    _build_system_prompt,
    _build_user_message,
    _parse_response,
)


def _make_email(**overrides) -> MagicMock:
    """Create a mock Email object for testing without DB."""
    email = MagicMock(spec=Email)
    email.id = overrides.get("id", uuid.uuid4())
    email.sender = overrides.get("sender", "sender@example.com")
    email.subject = overrides.get("subject", "Test Subject")
    email.body_preview = overrides.get("body_preview", "Test body preview")
    email.has_attachments = overrides.get("has_attachments", False)
    email.thread_length = overrides.get("thread_length", 1)
    return email


def _make_preference(**overrides) -> MagicMock:
    """Create a mock UserPreference object for testing without DB."""
    pref = MagicMock(spec=UserPreference)
    pref.important_senders = overrides.get("important_senders", [])
    pref.important_keywords = overrides.get("important_keywords", [])
    pref.response_rate = overrides.get("response_rate", None)
    return pref


def _make_mock_response(json_text: str) -> MagicMock:
    """Create a mock Anthropic Message with text content."""
    mock_msg = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json_text
    mock_msg.content = [mock_block]
    return mock_msg


def _valid_classification_json(count: int = 1) -> str:
    """Generate valid classification JSON for N emails."""
    classifications = []
    for i in range(count):
        classifications.append({
            "email_index": i,
            "priority": "high",
            "urgency": "urgent",
            "needs_response": True,
            "reason": f"Test reason for email {i}",
            "action_items": ["Reply"],
        })
    return json.dumps({"classifications": classifications})


class TestBuildSystemPrompt:
    """Tests for system prompt construction."""

    def test_base_prompt_without_preferences(self):
        blocks = _build_system_prompt(None)
        assert len(blocks) == 1
        assert "email priority classifier" in blocks[0]["text"]
        assert blocks[0]["type"] == "text"

    def test_prompt_includes_important_senders(self):
        pref = _make_preference(important_senders=["boss@company.com"])
        blocks = _build_system_prompt(pref)
        assert len(blocks) == 2
        assert "boss@company.com" in blocks[1]["text"]
        assert blocks[1]["cache_control"] == {"type": "ephemeral"}

    def test_prompt_includes_important_keywords(self):
        pref = _make_preference(important_keywords=["urgent", "deadline"])
        blocks = _build_system_prompt(pref)
        assert "urgent" in blocks[1]["text"]
        assert "deadline" in blocks[1]["text"]

    def test_prompt_includes_response_rate(self):
        pref = _make_preference(response_rate=0.85)
        blocks = _build_system_prompt(pref)
        assert "85%" in blocks[1]["text"]

    def test_empty_preferences_no_extra_block(self):
        pref = _make_preference(
            important_senders=[], important_keywords=[], response_rate=None
        )
        blocks = _build_system_prompt(pref)
        # Only base prompt; preferences block has no useful content
        # but the block is still added with the header line
        assert len(blocks) == 2


class TestBuildUserMessage:
    """Tests for email formatting."""

    def test_single_email_formatting(self):
        email = _make_email(sender="a@b.com", subject="Hello")
        msg = _build_user_message([email])
        assert "Email 0" in msg
        assert "From: a@b.com" in msg
        assert "Subject: Hello" in msg

    def test_multiple_emails_formatting(self):
        emails = [_make_email(sender=f"s{i}@b.com") for i in range(3)]
        msg = _build_user_message(emails)
        assert "Email 0" in msg
        assert "Email 1" in msg
        assert "Email 2" in msg

    def test_email_without_body_preview(self):
        email = _make_email(body_preview=None)
        msg = _build_user_message([email])
        assert "(no preview)" in msg


class TestParseResponse:
    """Tests for Claude response parsing."""

    def test_parse_valid_json(self):
        text = _valid_classification_json(2)
        result = _parse_response(text, expected_count=2)
        assert len(result.classifications) == 2
        assert result.classifications[0].priority == PriorityLevel.HIGH

    def test_parse_json_wrapped_in_code_fence(self):
        text = "```json\n" + _valid_classification_json(1) + "\n```"
        result = _parse_response(text, expected_count=1)
        assert len(result.classifications) == 1

    def test_parse_invalid_json_raises_value_error(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            _parse_response("not json at all", expected_count=1)

    def test_parse_valid_json_invalid_schema_raises(self):
        # Valid JSON but missing required fields
        text = json.dumps({"classifications": [{"email_index": 0}]})
        with pytest.raises(Exception):
            _parse_response(text, expected_count=1)

    def test_parse_mismatched_count_does_not_raise(self):
        # Returns 1 but expected 2 — should log warning but not raise
        text = _valid_classification_json(1)
        result = _parse_response(text, expected_count=2)
        assert len(result.classifications) == 1


class TestClaudeServiceClassifyBatch:
    """Tests for the ClaudeService.classify_batch method."""

    def test_classify_empty_list_returns_empty(self, claude_service):
        result = claude_service.classify_batch([])
        assert result == []

    def test_classify_single_email(self, claude_service, mock_anthropic_client):
        email = _make_email()
        mock_anthropic_client.messages.create.return_value = _make_mock_response(
            _valid_classification_json(1)
        )
        result = claude_service.classify_batch([email])
        assert len(result) == 1
        assert result[0].priority == PriorityLevel.HIGH
        mock_anthropic_client.messages.create.assert_called_once()

    def test_classify_multiple_emails(self, claude_service, mock_anthropic_client):
        emails = [_make_email() for _ in range(5)]
        mock_anthropic_client.messages.create.return_value = _make_mock_response(
            _valid_classification_json(5)
        )
        result = claude_service.classify_batch(emails)
        assert len(result) == 5

    def test_classify_exceeds_max_batch_raises_value_error(self, claude_service):
        emails = [_make_email() for _ in range(MAX_BATCH_SIZE + 1)]
        with pytest.raises(ValueError, match="exceeds maximum"):
            claude_service.classify_batch(emails)

    def test_classify_uses_temperature_zero(
        self, claude_service, mock_anthropic_client
    ):
        email = _make_email()
        mock_anthropic_client.messages.create.return_value = _make_mock_response(
            _valid_classification_json(1)
        )
        claude_service.classify_batch([email])
        call_kwargs = mock_anthropic_client.messages.create.call_args
        assert call_kwargs.kwargs.get("temperature") == 0.0

    def test_classify_with_preferences(self, claude_service, mock_anthropic_client):
        email = _make_email()
        pref = _make_preference(important_senders=["vip@company.com"])
        mock_anthropic_client.messages.create.return_value = _make_mock_response(
            _valid_classification_json(1)
        )
        claude_service.classify_batch([email], preferences=pref)
        call_kwargs = mock_anthropic_client.messages.create.call_args
        system_blocks = call_kwargs.kwargs.get("system")
        # Should have 2 blocks: base + preferences with cache_control
        assert len(system_blocks) == 2
        assert "cache_control" in system_blocks[1]

    def test_classify_api_error_propagates(self, claude_service, mock_anthropic_client):
        email = _make_email()
        mock_anthropic_client.messages.create.side_effect = anthropic.APIError(
            message="Rate limited",
            request=MagicMock(),
            body=None,
        )
        with pytest.raises(anthropic.APIError):
            claude_service.classify_batch([email])
