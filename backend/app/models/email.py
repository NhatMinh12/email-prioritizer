"""Email model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.classification import Classification
    from app.models.user import User


class Email(TimestampMixin, Base):
    __tablename__ = "emails"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gmail_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sender: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    thread_length: Mapped[int] = mapped_column(Integer, default=1)

    __table_args__ = (
        UniqueConstraint("user_id", "gmail_id", name="uq_user_gmail_id"),
        Index("ix_emails_user_received", "user_id", "received_at"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="emails")
    classification: Mapped[Optional["Classification"]] = relationship(
        back_populates="email", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Email {self.gmail_id} from={self.sender}>"
