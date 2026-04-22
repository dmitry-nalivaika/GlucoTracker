"""Unit tests for SessionService idle and expiry logic — T051.

Uses in-memory SQLite via test_db fixture.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from glucotrack.domain.session import InsufficientEntriesError
from glucotrack.models.session import SessionStatus
from glucotrack.repositories.session_repository import SessionRepository
from glucotrack.services.session_service import IdleGapDetected, SessionService
from glucotrack.storage.local_storage import StorageRepository


def _make_service(
    db, idle_threshold_minutes: int = 30, idle_expiry_hours: int = 24
) -> SessionService:
    storage = MagicMock(spec=StorageRepository)
    storage.save_file.return_value = "users/1/sessions/s1/food.jpg"
    return SessionService(
        db=db,
        storage=storage,
        idle_threshold_minutes=idle_threshold_minutes,
        idle_expiry_hours=idle_expiry_hours,
    )


class TestSessionServiceIdleGap:
    """Idle gap detection (FR-013)."""

    @pytest.mark.asyncio
    async def test_idle_gap_exceeds_threshold_raises(self, test_db) -> None:
        """IdleGapDetected raised when idle gap > threshold."""
        service = _make_service(test_db, idle_threshold_minutes=30)

        # Open a session
        session, _ = await service.get_or_open_session(telegram_user_id=501)
        await test_db.commit()

        # Simulate 35-minute idle gap by patching last_input_at
        sess_repo = SessionRepository(test_db)
        s = await sess_repo.get_open_session(user_id=501)
        s.last_input_at = datetime.now(tz=UTC) - timedelta(minutes=35)
        await test_db.commit()

        with pytest.raises(IdleGapDetected) as exc_info:
            await service.get_or_open_session(telegram_user_id=501)

        assert exc_info.value.idle_minutes > 30

    @pytest.mark.asyncio
    async def test_idle_gap_within_threshold_does_not_raise(self, test_db) -> None:
        """No exception when idle gap is below threshold."""
        service = _make_service(test_db, idle_threshold_minutes=30)

        session, _ = await service.get_or_open_session(telegram_user_id=502)
        await test_db.commit()

        # Recent activity — within threshold
        sess_repo = SessionRepository(test_db)
        s = await sess_repo.get_open_session(user_id=502)
        s.last_input_at = datetime.now(tz=UTC) - timedelta(minutes=10)
        await test_db.commit()

        # Should not raise
        session2, is_new = await service.get_or_open_session(telegram_user_id=502)
        assert is_new is False
        assert session2.id == session.id

    @pytest.mark.asyncio
    async def test_force_new_opens_new_session(self, test_db) -> None:
        """force_new=True creates a new session regardless of idle gap."""
        service = _make_service(test_db)
        session1, _ = await service.get_or_open_session(telegram_user_id=503)
        await test_db.commit()

        session2, is_new = await service.get_or_open_session(telegram_user_id=503, force_new=True)
        await test_db.commit()

        assert is_new is True
        assert session2.id != session1.id


class TestSessionServiceExpiry:
    """Auto-expiry (FR-012)."""

    @pytest.mark.asyncio
    async def test_expire_idle_sessions_expires_old_sessions(self, test_db) -> None:
        """Sessions idle beyond expiry threshold are expired."""
        service = _make_service(test_db, idle_expiry_hours=24)

        # Create session
        sess_repo = SessionRepository(test_db)
        session = await sess_repo.create_session(user_id=601)
        # Age the session beyond 24h
        session.last_input_at = datetime.now(tz=UTC) - timedelta(hours=25)
        await test_db.commit()

        count = await service.expire_idle_sessions()
        assert count >= 1

        expired = await sess_repo.get_session(user_id=601, session_id=session.id)
        assert expired is not None
        assert expired.status == SessionStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_expire_idle_sessions_spares_recent_sessions(self, test_db) -> None:
        """Sessions within expiry threshold are NOT expired."""
        service = _make_service(test_db, idle_expiry_hours=24)

        sess_repo = SessionRepository(test_db)
        session = await sess_repo.create_session(user_id=602)
        # Recent session — only 2h idle
        session.last_input_at = datetime.now(tz=UTC) - timedelta(hours=2)
        await test_db.commit()

        await service.expire_idle_sessions()

        still_open = await sess_repo.get_session(user_id=602, session_id=session.id)
        assert still_open is not None
        assert still_open.status == SessionStatus.OPEN


class TestSessionServiceCompletion:
    """Session completion validation."""

    @pytest.mark.asyncio
    async def test_complete_session_without_entries_raises(self, test_db) -> None:
        """InsufficientEntriesError raised when completing a session with no entries."""
        service = _make_service(test_db)
        await service.get_or_open_session(telegram_user_id=701)
        await test_db.commit()

        with pytest.raises(InsufficientEntriesError):
            await service.complete_session(telegram_user_id=701)
