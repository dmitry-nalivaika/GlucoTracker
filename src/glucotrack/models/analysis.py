"""AIAnalysis and TrendAnalysis ORM models.

Both models are required from day one so the data model supports trend
analysis from the first session (spec Assumptions, FR-014).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from glucotrack.models.base import Base, new_uuid, utcnow


class AIAnalysis(Base):  # type: ignore[misc]
    """The structured result of analysing a single session with Claude."""

    __tablename__ = "ai_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, unique=True, index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # JSON columns stored as TEXT; migrate to JSONB on PostgreSQL/Azure SQL
    nutrition_json: Mapped[str] = mapped_column(Text, nullable=False)
    glucose_curve_json: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_json: Mapped[str] = mapped_column(Text, nullable=False)
    recommendations_json: Mapped[str] = mapped_column(Text, nullable=False)
    within_target_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    session: Mapped[Session] = relationship("Session", back_populates="analysis")  # type: ignore[name-defined]
    miro_card: Mapped[MiroCard | None] = relationship(  # type: ignore[name-defined]
        "MiroCard",
        primaryjoin="and_(MiroCard.source_id == AIAnalysis.id, MiroCard.source_type == 'analysis')",
        foreign_keys="[MiroCard.source_id]",
        uselist=False,
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<AIAnalysis id={self.id} session_id={self.session_id}>"


class TrendAnalysis(Base):  # type: ignore[misc]
    """Cross-session analysis result covering a user's historical sessions.

    Required in data model from day one (spec Assumptions, FR-014).
    Full trend analysis command is deferred to a later sprint (P4).
    """

    __tablename__ = "trend_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    session_count: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    session_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    patterns_json: Mapped[str] = mapped_column(Text, nullable=False)
    recommendations_json: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    def __repr__(self) -> str:
        return f"<TrendAnalysis id={self.id} user_id={self.user_id} sessions={self.session_count}>"
