"""Data models for the application."""

from app.models.base import PriorityLevel, UrgencyLevel  # noqa: F401
from app.models.classification import Classification  # noqa: F401
from app.models.email import Email  # noqa: F401
from app.models.user import User, UserPreference  # noqa: F401

__all__ = [
    "Classification",
    "Email",
    "PriorityLevel",
    "UrgencyLevel",
    "User",
    "UserPreference",
]