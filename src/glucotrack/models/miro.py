"""MiroCard ORM model.

A read-only visualisation artefact created from an AIAnalysis or TrendAnalysis.
References the source but is not the source of truth.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from glucotrack.models.base import Base, new_uuid, utcnow


class MiroCardSourceType(str, enum.Enum):
    ANALYSIS = "analysis"
    TREND = "trend"


class MiroCardStatus(str, enum.Enum):
    PENDING = "pending"
    CREATED = "created"
    FAILED = "failed"


class MiroCard(Base):
    """Record of a card created (or attempted) on the Miro board."""

    __tablename__ = "miro_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    source_type: Mapped[MiroCardSourceType] = mapped_column(
        Enum(MiroCardSourceType), nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    miro_board_id: Mapped[str] = mapped_column(Text, nullable=False)
    miro_card_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MiroCardStatus] = mapped_column(
        Enum(MiroCardStatus), nullable=False, default=MiroCardStatus.PENDING
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<MiroCard id={self.id} source_type={self.source_type} status={self.status}>"
        )
