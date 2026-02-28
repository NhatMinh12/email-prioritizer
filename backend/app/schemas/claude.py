"""Schemas for parsing Claude API classification responses.

Separate from ClassificationResponse (which includes DB fields like id,
email_id, classified_at) because these schemas validate only the data
Claude returns in its JSON output.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.models.base import PriorityLevel, UrgencyLevel


class SingleEmailClassification(BaseModel):
    """Classification result for a single email, as returned by Claude."""

    email_index: int = Field(
        ..., description="0-based index of the email in the batch"
    )
    priority: PriorityLevel
    urgency: UrgencyLevel
    needs_response: bool
    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Brief explanation of why this priority was assigned",
    )
    action_items: Optional[list[str]] = None


class BatchClassificationResponse(BaseModel):
    """Claude's response for a batch of emails."""

    classifications: list[SingleEmailClassification]
