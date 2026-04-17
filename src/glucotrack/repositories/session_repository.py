"""SessionRepository — data access for sessions and their entries.

ALL methods take user_id and scope queries by it (Constitution II).
No query runs without user context.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from glucotrack.models.base import new_uuid, utcnow
from glucotrack.models.entries import ActivityEntry, CGMEntry, FoodEntry
from glucotrack.models.session import Session, SessionStatus

logger = logging.getLogger(__name__)


class UserSessionMismatchError(Exception):
    """Raised when a user_id does not match the session's owner."""


class SessionRepository:
    """Async repository for Session, FoodEntry, CGMEntry, ActivityEntry."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_session(self, user_id: int) -> Session:
        """Create and persist a new open Session for user_id."""
        now = utcnow()
        session = Session(
            id=new_uuid(),
            user_id=user_id,
            status=SessionStatus.OPEN,
            created_at=now,
            last_input_at=now,
        )
        self._db.add(session)
        await self._db.flush()
        await self._db.refresh(session)
        logger.debug("Created session id=%s user_id=%d", session.id, user_id)
        return session

    async def get_open_session(self, user_id: int) -> Session | None:
        """Return the open Session for user_id, or None.

        Constitution II: query scoped by user_id.
        """
        result = await self._db.execute(
            select(Session).where(
                and_(
                    Session.user_id == user_id,
                    Session.status == SessionStatus.OPEN,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_session(self, user_id: int, session_id: str) -> Session | None:
        """Return a specific session scoped to user_id."""
        result = await self._db.execute(
            select(Session).where(and_(Session.user_id == user_id, Session.id == session_id))
        )
        return result.scalar_one_or_none()

    async def _verify_session_ownership(self, user_id: int, session_id: str) -> Session:
        """Raise UserSessionMismatchError if session doesn't belong to user_id."""
        session = await self.get_session(user_id, session_id)
        if session is None:
            raise UserSessionMismatchError(
                f"Session {session_id!r} not found for user_id={user_id}"
            )
        return session

    async def add_food_entry(
        self,
        user_id: int,
        session_id: str,
        file_path: str,
        telegram_file_id: str,
        description: str | None = None,
    ) -> FoodEntry:
        """Add a FoodEntry to session_id owned by user_id."""
        await self._verify_session_ownership(user_id, session_id)
        now = utcnow()
        entry = FoodEntry(
            id=new_uuid(),
            session_id=session_id,
            user_id=user_id,
            file_path=file_path,
            telegram_file_id=telegram_file_id,
            description=description,
            created_at=now,
        )
        self._db.add(entry)
        await self._update_last_input(session_id, user_id, now)
        await self._db.flush()
        await self._db.refresh(entry)
        return entry

    async def add_cgm_entry(
        self,
        user_id: int,
        session_id: str,
        file_path: str,
        telegram_file_id: str,
        timing_label: str = "unspecified",
    ) -> CGMEntry:
        """Add a CGMEntry to session_id owned by user_id."""
        await self._verify_session_ownership(user_id, session_id)
        now = utcnow()
        entry = CGMEntry(
            id=new_uuid(),
            session_id=session_id,
            user_id=user_id,
            file_path=file_path,
            telegram_file_id=telegram_file_id,
            timing_label=timing_label,
            created_at=now,
        )
        self._db.add(entry)
        await self._update_last_input(session_id, user_id, now)
        await self._db.flush()
        await self._db.refresh(entry)
        return entry

    async def add_activity_entry(
        self,
        user_id: int,
        session_id: str,
        description: str,
    ) -> ActivityEntry:
        """Add an ActivityEntry to session_id owned by user_id."""
        await self._verify_session_ownership(user_id, session_id)
        now = utcnow()
        entry = ActivityEntry(
            id=new_uuid(),
            session_id=session_id,
            user_id=user_id,
            description=description,
            created_at=now,
        )
        self._db.add(entry)
        await self._update_last_input(session_id, user_id, now)
        await self._db.flush()
        await self._db.refresh(entry)
        return entry

    async def complete_session(self, user_id: int, session_id: str) -> Session:
        """Transition session to COMPLETED status."""
        session = await self._verify_session_ownership(user_id, session_id)
        session.status = SessionStatus.COMPLETED
        session.completed_at = utcnow()
        await self._db.flush()
        await self._db.refresh(session)
        return session

    async def expire_session(self, user_id: int, session_id: str) -> Session:
        """Transition session to EXPIRED status."""
        session = await self._verify_session_ownership(user_id, session_id)
        session.status = SessionStatus.EXPIRED
        session.expired_at = utcnow()
        await self._db.flush()
        await self._db.refresh(session)
        return session

    async def mark_analysed(self, user_id: int, session_id: str) -> Session:
        """Transition session to ANALYSED status."""
        session = await self._verify_session_ownership(user_id, session_id)
        session.status = SessionStatus.ANALYSED
        await self._db.flush()
        await self._db.refresh(session)
        return session

    async def get_entry_counts(self, user_id: int, session_id: str) -> dict[str, int]:
        """Return counts of each entry type for the session, scoped by user_id."""
        await self._verify_session_ownership(user_id, session_id)

        food_result = await self._db.execute(
            select(FoodEntry).where(
                and_(FoodEntry.session_id == session_id, FoodEntry.user_id == user_id)
            )
        )
        cgm_result = await self._db.execute(
            select(CGMEntry).where(
                and_(CGMEntry.session_id == session_id, CGMEntry.user_id == user_id)
            )
        )
        activity_result = await self._db.execute(
            select(ActivityEntry).where(
                and_(ActivityEntry.session_id == session_id, ActivityEntry.user_id == user_id)
            )
        )

        return {
            "food": len(food_result.scalars().all()),
            "cgm": len(cgm_result.scalars().all()),
            "activity": len(activity_result.scalars().all()),
        }

    async def _get_sessions_for_expiry_job(self, idle_before_dt: Any) -> list[Session]:
        """Return all open sessions idle before idle_before_dt.

        ADMIN/SYSTEM USE ONLY — called exclusively by SessionService.expire_idle_sessions().
        This query is intentionally cross-user: the background expiry job must inspect all
        users' sessions to enforce FR-012. Each returned session is subsequently processed
        with its own session.user_id (see SessionService.expire_idle_sessions).

        Constitution II exemption tracked in GitHub issue #N — admin-operation exception.
        """
        result = await self._db.execute(
            select(Session).where(
                and_(
                    Session.status == SessionStatus.OPEN,
                    Session.last_input_at < idle_before_dt,
                )
            )
        )
        return list(result.scalars().all())

    async def get_analysed_sessions_for_trend(
        self, user_id: int, min_count: int = 3
    ) -> list[Session]:
        """Return analysed sessions for user_id.

        Raises InsufficientDataError if fewer than min_count sessions exist (FR-015).
        Constitution II: scoped by user_id.
        """
        from glucotrack.repositories.analysis_repository import InsufficientDataError

        result = await self._db.execute(
            select(Session).where(
                and_(
                    Session.user_id == user_id,
                    Session.status == SessionStatus.ANALYSED,
                )
            )
        )
        sessions = list(result.scalars().all())
        if len(sessions) < min_count:
            raise InsufficientDataError(current_count=len(sessions), required_count=min_count)
        return sessions

    async def _update_last_input(self, session_id: str, user_id: int, ts: Any) -> None:
        """Update last_input_at on the session.

        Constitution II: scoped by both session_id AND user_id.
        """
        result = await self._db.execute(
            select(Session).where(and_(Session.id == session_id, Session.user_id == user_id))
        )
        session = result.scalar_one_or_none()
        if session is not None:
            session.last_input_at = ts
