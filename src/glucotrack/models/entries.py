"""Entry ORM models: FoodEntry, CGMEntry, ActivityEntry.

Each entry belongs to exactly one Session. All include user_id for direct
user scoping (Constitution II — every query must include user_id predicate).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from glucotrack.models.base import Base, new_uuid, utcnow


class FoodEntry(Base):
    """A food photograph within a session."""

    __tablename__ = "food_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_file_id: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    session: Mapped["Session"] = relationship("Session", back_populates="food_entries")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<FoodEntry id={self.id} session_id={self.session_id}>"


class CGMEntry(Base):
    """A CGM screenshot within a session, labelled with a timing context."""

    __tablename__ = "cgm_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_file_id: Mapped[str] = mapped_column(Text, nullable=False)
    timing_label: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    session: Mapped["Session"] = relationship("Session", back_populates="cgm_entries")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<CGMEntry id={self.id} timing={self.timing_label}>"


class ActivityEntry(Base):
    """A free-text description of physical activity within a session."""

    __tablename__ = "activity_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    session: Mapped["Session"] = relationship("Session", back_populates="activity_entries")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<ActivityEntry id={self.id} session_id={self.session_id}>"
