"""Pydantic schemas for request/response validation."""

from app.schemas.classification import (  # noqa: F401
    ClassificationFeedback,
    ClassificationResponse,
)
from app.schemas.common import PaginatedResponse, PaginationParams  # noqa: F401
from app.schemas.email import (  # noqa: F401
    EmailCreate,
    EmailListResponse,
    EmailResponse,
)
from app.schemas.user import (  # noqa: F401
    UserCreate,
    UserPreferenceResponse,
    UserPreferenceUpdate,
    UserResponse,
)
