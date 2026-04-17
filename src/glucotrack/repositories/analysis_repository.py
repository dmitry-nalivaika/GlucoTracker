"""AnalysisRepository — data access for AIAnalysis and TrendAnalysis.

All queries scoped by user_id (Constitution II).
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from glucotrack.models.analysis import AIAnalysis, TrendAnalysis
from glucotrack.models.base import new_uuid, utcnow

logger = logging.getLogger(__name__)


class InsufficientDataError(Exception):
    """Raised when too few sessions exist for trend analysis (FR-015)."""

    def __init__(self, current_count: int, required_count: int) -> None:
        self.current_count = current_count
        self.required_count = required_count
        super().__init__(
            f"Trend analysis requires ≥{required_count} analysed sessions "
            f"(you have {current_count})."
        )


class AnalysisRepository:
    """Async repository for AIAnalysis and TrendAnalysis."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save_analysis(
        self,
        user_id: int,
        session_id: str,
        nutrition: dict,
        glucose_curve: list,
        correlation: dict,
        recommendations: list,
        within_target_notes: str | None,
        raw_response: str,
    ) -> AIAnalysis:
        """Persist an AIAnalysis for session_id owned by user_id."""
        analysis = AIAnalysis(
            id=new_uuid(),
            session_id=session_id,
            user_id=user_id,
            nutrition_json=json.dumps(nutrition),
            glucose_curve_json=json.dumps(glucose_curve),
            correlation_json=json.dumps(correlation),
            recommendations_json=json.dumps(recommendations),
            within_target_notes=within_target_notes,
            raw_response=raw_response,
            created_at=utcnow(),
        )
        self._db.add(analysis)
        await self._db.flush()
        await self._db.refresh(analysis)
        logger.debug("Saved analysis id=%s session_id=%s", analysis.id, session_id)
        return analysis

    async def get_analysis_by_session(
        self, user_id: int, session_id: str
    ) -> AIAnalysis | None:
        """Return the AIAnalysis for session_id scoped to user_id, or None."""
        result = await self._db.execute(
            select(AIAnalysis).where(
                and_(
                    AIAnalysis.session_id == session_id,
                    AIAnalysis.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_analyses_for_user(self, user_id: int) -> list[AIAnalysis]:
        """Return all analyses for user_id, ordered by creation time."""
        result = await self._db.execute(
            select(AIAnalysis)
            .where(AIAnalysis.user_id == user_id)
            .order_by(AIAnalysis.created_at)
        )
        return list(result.scalars().all())
