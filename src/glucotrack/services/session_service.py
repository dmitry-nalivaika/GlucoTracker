"""SessionService — orchestrates session lifecycle.

Handles idle gap detection (FR-013) and session auto-expiry (FR-012).
"""

from __future__ import annotations

import logging
from datetime import UTC, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from glucotrack.domain.session import SessionStateMachine
from glucotrack.domain.user import get_or_create_user
from glucotrack.models.base import utcnow
from glucotrack.models.session import Session
from glucotrack.repositories.session_repository import SessionRepository
from glucotrack.storage.local_storage import StorageRepository

logger = logging.getLogger(__name__)


class IdleGapDetected(Exception):  # noqa: N818
    """Raised when a user sends a message after idle_threshold minutes since last input."""

    def __init__(self, session: Session, idle_minutes: float) -> None:
        self.session = session
        self.idle_minutes = idle_minutes
        super().__init__(f"Idle gap of {idle_minutes:.1f} minutes detected.")


class SessionService:
    """Orchestrates user creation, session management, and entry persistence."""

    def __init__(
        self,
        db: AsyncSession,
        storage: StorageRepository,
        idle_threshold_minutes: int = 30,
        idle_expiry_hours: int = 24,
    ) -> None:
        self._db = db
        self._storage = storage
        self._idle_threshold = idle_threshold_minutes
        self._idle_expiry_hours = idle_expiry_hours
        self._sm = SessionStateMachine()
        self._sess_repo = SessionRepository(db)

    async def get_or_open_session(
        self, telegram_user_id: int, *, force_new: bool = False
    ) -> tuple[Session, bool]:
        """Return the open session or create one.

        Args:
            telegram_user_id: The user's Telegram ID.
            force_new: If True, always create a new session (user chose "Start new").

        Returns:
            (session, is_new) tuple.

        Raises:
            IdleGapDetected: If idle gap > threshold and force_new is False.
        """
        await get_or_create_user(self._db, telegram_user_id)
        session = await self._sess_repo.get_open_session(user_id=telegram_user_id)

        if force_new or session is None:
            if session is not None and force_new:
                # Auto-close the existing session before opening a new one
                await self._try_complete_or_expire(telegram_user_id, session)
            new_session = await self._sess_repo.create_session(user_id=telegram_user_id)
            return new_session, True

        # Check idle gap (FR-013)
        now = utcnow()
        last_input = session.last_input_at
        if last_input.tzinfo is None:
            last_input = last_input.replace(tzinfo=UTC)
        idle_minutes = (now - last_input).total_seconds() / 60
        if idle_minutes > self._idle_threshold:
            raise IdleGapDetected(session, idle_minutes)

        return session, False

    async def handle_photo(
        self,
        telegram_user_id: int,
        file_data: bytes,
        telegram_file_id: str,
        entry_type: str,
        timing_label: str = "unspecified",
        description: str | None = None,
    ) -> None:
        """Save a photo and add it to the user's open session.

        Args:
            telegram_user_id: User identity.
            file_data: Raw image bytes.
            telegram_file_id: Telegram file_id for reference.
            entry_type: 'food' or 'cgm'.
            timing_label: CGM timing label (required when entry_type='cgm').
            description: Optional food description.
        """
        session, _ = await self.get_or_open_session(telegram_user_id)
        ext = "jpg"
        if entry_type == "food":
            filename = f"food_{telegram_file_id[:8]}.{ext}"
        else:
            filename = f"cgm_{telegram_file_id[:8]}.{ext}"

        file_path = self._storage.save_file(telegram_user_id, session.id, filename, file_data)

        if entry_type == "food":
            await self._sess_repo.add_food_entry(
                user_id=telegram_user_id,
                session_id=session.id,
                file_path=file_path,
                telegram_file_id=telegram_file_id,
                description=description,
            )
        else:
            await self._sess_repo.add_cgm_entry(
                user_id=telegram_user_id,
                session_id=session.id,
                file_path=file_path,
                telegram_file_id=telegram_file_id,
                timing_label=timing_label,
            )

    async def handle_activity(self, telegram_user_id: int, text: str) -> None:
        """Record an activity description in the user's open session."""
        session, _ = await self.get_or_open_session(telegram_user_id)
        await self._sess_repo.add_activity_entry(
            user_id=telegram_user_id,
            session_id=session.id,
            description=text[:500],  # validate max length
        )

    async def complete_session(self, telegram_user_id: int) -> Session:
        """Validate entry counts and mark session COMPLETED.

        Raises:
            InsufficientEntriesError: If < 1 food or < 1 CGM entry.
        """
        session = await self._sess_repo.get_open_session(user_id=telegram_user_id)
        if session is None:
            raise ValueError("No open session found.")

        counts = await self._sess_repo.get_entry_counts(
            user_id=telegram_user_id, session_id=session.id
        )
        self._sm.validate_completion(food_count=counts["food"], cgm_count=counts["cgm"])
        return await self._sess_repo.complete_session(
            user_id=telegram_user_id, session_id=session.id
        )

    async def get_entry_counts(self, telegram_user_id: int) -> dict[str, int]:
        """Return entry counts for the user's open session."""
        session = await self._sess_repo.get_open_session(user_id=telegram_user_id)
        if session is None:
            return {"food": 0, "cgm": 0, "activity": 0}
        result: dict[str, int] = await self._sess_repo.get_entry_counts(
            user_id=telegram_user_id, session_id=session.id
        )
        return result

    async def expire_idle_sessions(self) -> int:
        """Expire all open sessions idle beyond expiry threshold (FR-012).

        Returns:
            Number of sessions expired.
        """
        cutoff = utcnow() - timedelta(hours=self._idle_expiry_hours)
        idle_sessions = await self._sess_repo._get_sessions_for_expiry_job(cutoff)
        count = 0
        for session in idle_sessions:
            await self._sess_repo.expire_session(user_id=session.user_id, session_id=session.id)
            logger.info("Expired idle session id=%s user_id=%d", session.id, session.user_id)
            count += 1
        return count

    async def _try_complete_or_expire(self, user_id: int, session: Session) -> None:
        """Complete session if it has entries, otherwise expire it."""
        counts = await self._sess_repo.get_entry_counts(user_id=user_id, session_id=session.id)
        if counts["food"] >= 1 and counts["cgm"] >= 1:
            await self._sess_repo.complete_session(user_id=user_id, session_id=session.id)
        else:
            await self._sess_repo.expire_session(user_id=user_id, session_id=session.id)
