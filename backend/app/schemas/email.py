"""Email schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.classification import ClassificationResponse


class EmailCreate(BaseModel):
    gmail_id: str
    sender: str
    subject: str
    body_preview: Optional[str] = None
    received_at: datetime
    has_attachments: bool = False
    thread_length: int = 1


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    gmail_id: str
    sender: str
    subject: str
    body_preview: Optional[str] = None
    received_at: datetime
    has_attachments: bool
    thread_length: int
    classification: Optional[ClassificationResponse] = None


class EmailListResponse(BaseModel):
    emails: list[EmailResponse]
    total: int
    page: int
    page_size: int
