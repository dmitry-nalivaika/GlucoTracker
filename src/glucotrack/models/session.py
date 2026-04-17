"""Session ORM model.

A session groups one meal/activity event: food photos, CGM screenshots,
activity notes. Status transitions: open → completed → analysed / open → expired.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from glucotrack.models.base import Base, new_uuid, utcnow


class SessionStatus(str, enum.Enum):
    OPEN = "open"
    COMPLETED = "completed"
    ANALYSED = "analysed"
    EXPIRED = "expired"


class Session(Base):
    """A bounded collection of user inputs representing one meal/activity event."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_user_id"), nullable=False, index=True
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), nullable=False, default=SessionStatus.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_input_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")  # type: ignore[name-defined]
    food_entries: Mapped[list["FoodEntry"]] = relationship(  # type: ignore[name-defined]
        "FoodEntry", back_populates="session", cascade="all, delete-orphan"
    )
    cgm_entries: Mapped[list["CGMEntry"]] = relationship(  # type: ignore[name-defined]
        "CGMEntry", back_populates="session", cascade="all, delete-orphan"
    )
    activity_entries: Mapped[list["ActivityEntry"]] = relationship(  # type: ignore[name-defined]
        "ActivityEntry", back_populates="session", cascade="all, delete-orphan"
    )
    analysis: Mapped["AIAnalysis | None"] = relationship(  # type: ignore[name-defined]
        "AIAnalysis", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id} status={self.status}>"
