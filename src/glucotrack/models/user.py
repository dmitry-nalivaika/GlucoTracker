"""User ORM model.

Identity is the Telegram user ID (BIGINT). Created automatically on first
contact; no password or email in MVP.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from glucotrack.models.base import Base, utcnow


class User(Base):
    """A GlucoTrack user identified by their Telegram user ID."""

    __tablename__ = "users"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(  # type: ignore[name-defined]
        "Session", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User telegram_user_id={self.telegram_user_id}>"
