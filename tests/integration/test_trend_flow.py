"""Integration tests for US4 trend data readiness — T047.

Verifies that `get_analysed_sessions_for_trend` correctly scopes by user_id
and raises InsufficientDataError when fewer than min_count sessions exist.
"""

from __future__ import annotations

import pytest

from glucotrack.domain.user import get_or_create_user
from glucotrack.models.session import SessionStatus
from glucotrack.repositories.analysis_repository import InsufficientDataError
from glucotrack.repositories.session_repository import SessionRepository


async def _seed_analysed_sessions(db, user_id: int, count: int) -> list:
    """Create `count` analysed sessions for user_id."""
    repo = SessionRepository(db)
    sessions = []
    for _ in range(count):
        session = await repo.create_session(user_id=user_id)
        # Manually set status to ANALYSED via repo helper
        await repo.mark_analysed(user_id, session.id)
        await db.commit()
        sessions.append(session)
    return sessions


class TestTrendFlow:
    """US4: trend data readiness — user isolation and InsufficientDataError."""

    @pytest.mark.asyncio
    async def test_returns_all_analysed_sessions_for_user(self, test_db) -> None:
        user = await get_or_create_user(test_db, telegram_user_id=301)
        await _seed_analysed_sessions(test_db, user.telegram_user_id, 5)

        repo = SessionRepository(test_db)
        sessions = await repo.get_analysed_sessions_for_trend(
            user_id=user.telegram_user_id, min_count=3
        )

        assert len(sessions) == 5
        for s in sessions:
            assert s.user_id == user.telegram_user_id
            assert s.status == SessionStatus.ANALYSED

    @pytest.mark.asyncio
    async def test_user_isolation(self, test_db) -> None:
        """User B's sessions must not appear in user A's trend query."""
        user_a = await get_or_create_user(test_db, telegram_user_id=302)
        user_b = await get_or_create_user(test_db, telegram_user_id=303)

        await _seed_analysed_sessions(test_db, user_a.telegram_user_id, 5)
        await _seed_analysed_sessions(test_db, user_b.telegram_user_id, 3)

        repo = SessionRepository(test_db)
        sessions = await repo.get_analysed_sessions_for_trend(
            user_id=user_a.telegram_user_id, min_count=3
        )

        assert len(sessions) == 5
        assert all(s.user_id == user_a.telegram_user_id for s in sessions)

    @pytest.mark.asyncio
    async def test_insufficient_data_raises_error(self, test_db) -> None:
        """InsufficientDataError raised when count < min_count (FR-015)."""
        user = await get_or_create_user(test_db, telegram_user_id=304)
        await _seed_analysed_sessions(test_db, user.telegram_user_id, 2)

        repo = SessionRepository(test_db)
        with pytest.raises(InsufficientDataError) as exc_info:
            await repo.get_analysed_sessions_for_trend(user_id=user.telegram_user_id, min_count=3)

        assert exc_info.value.current_count == 2
        assert exc_info.value.required_count == 3

    @pytest.mark.asyncio
    async def test_zero_sessions_raises_error_with_zero_count(self, test_db) -> None:
        """Brand new user with no sessions raises InsufficientDataError with count=0."""
        user = await get_or_create_user(test_db, telegram_user_id=305)

        repo = SessionRepository(test_db)
        with pytest.raises(InsufficientDataError) as exc_info:
            await repo.get_analysed_sessions_for_trend(user_id=user.telegram_user_id, min_count=3)

        assert exc_info.value.current_count == 0
