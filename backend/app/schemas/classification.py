"""Classification schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import PriorityLevel, UrgencyLevel


class ClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email_id: uuid.UUID
    priority: PriorityLevel
    urgency: UrgencyLevel
    needs_response: bool
    reason: str
    action_items: Optional[list] = None
    classified_at: datetime
    feedback: Optional[str] = None


class ClassificationFeedback(BaseModel):
    feedback: str = Field(
        ..., pattern="^(correct|incorrect|adjusted)$",
        description="User feedback on the classification accuracy",
    )
