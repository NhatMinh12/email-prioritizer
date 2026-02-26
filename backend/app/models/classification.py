"""Classification model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import PriorityLevel, UrgencyLevel
from app.models.email import Email


class Classification(Base):
    __tablename__ = "classifications"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    email_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("emails.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    priority: Mapped[PriorityLevel] = mapped_column(
        Enum(PriorityLevel, native_enum=True, name="prioritylevel"),
        nullable=False,
    )
    urgency: Mapped[UrgencyLevel] = mapped_column(
        Enum(UrgencyLevel, native_enum=True, name="urgencylevel"),
        nullable=False,
    )
    needs_response: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    action_items: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    classified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    feedback: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    email: Mapped["Email"] = relationship(back_populates="classification")

    def __repr__(self) -> str:
        return f"<Classification email_id={self.email_id} priority={self.priority}>"
