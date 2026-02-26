"""User and UserPreference schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime
    updated_at: datetime


class UserPreferenceUpdate(BaseModel):
    important_senders: Optional[list[str]] = None
    important_keywords: Optional[list[str]] = None
    response_rate: Optional[float] = None


class UserPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    important_senders: list
    important_keywords: list
    response_rate: Optional[float]
    updated_at: datetime
