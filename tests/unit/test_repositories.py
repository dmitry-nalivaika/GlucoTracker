"""Unit tests for repositories — T023."""
from __future__ import annotations

import pytest

from glucotrack.models.base import new_uuid
from glucotrack.models.session import SessionStatus
from glucotrack.repositories.session_repository import SessionRepository
from glucotrack.repositories.user_repository import UserRepository


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.mark.asyncio
    async def test_create_user(self, test_db):
        repo = UserRepository(test_db)
        user = await repo.create(telegram_user_id=100)
        assert user.telegram_user_id == 100

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_user(self, test_db):
        repo = UserRepository(test_db)
        await repo.create(telegram_user_id=100)
        user = await repo.get_by_telegram_id(100)
        assert user is not None
        assert user.telegram_user_id == 100

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_returns_none_for_missing(self, test_db):
        repo = UserRepository(test_db)
        user = await repo.get_by_telegram_id(999999)
        assert user is None

    @pytest.mark.asyncio
    async def test_update_last_seen(self, test_db):
        import asyncio
        repo = UserRepository(test_db)
        user = await repo.create(telegram_user_id=100)
        original = user.last_seen_at
        await asyncio.sleep(0.01)
        updated = await repo.update_last_seen(100)
        assert updated.last_seen_at >= original


class TestSessionRepository:
    """Tests for SessionRepository with user_id isolation."""

    @pytest.mark.asyncio
    async def test_create_session(self, test_db, sample_user):
        repo = SessionRepository(test_db)
        session = await repo.create_session(user_id=sample_user.telegram_user_id)
        assert session.user_id == sample_user.telegram_user_id
        assert session.status == SessionStatus.OPEN

    @pytest.mark.asyncio
    async def test_get_open_session_returns_none_when_none(self, test_db, sample_user):
        repo = SessionRepository(test_db)
        result = await repo.get_open_session(user_id=sample_user.telegram_user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_open_session_returns_open_session(self, test_db, sample_user):
        repo = SessionRepository(test_db)
        created = await repo.create_session(user_id=sample_user.telegram_user_id)
        fetched = await repo.get_open_session(user_id=sample_user.telegram_user_id)
        assert fetched is not None
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_cross_user_isolation_open_session(self, test_db):
        """User A cannot see User B's session — Constitution II."""
        user_repo = UserRepository(test_db)
        user_a = await user_repo.create(telegram_user_id=1001)
        user_b = await user_repo.create(telegram_user_id=1002)
        sess_repo = SessionRepository(test_db)
        await sess_repo.create_session(user_id=user_a.telegram_user_id)
        result = await sess_repo.get_open_session(user_id=user_b.telegram_user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_add_food_entry(self, test_db, sample_user, sample_session):
        repo = SessionRepository(test_db)
        entry = await repo.add_food_entry(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            file_path="users/100/sessions/s1/food_001.jpg",
            telegram_file_id="tg_file_001",
            description="pasta",
        )
        assert entry.user_id == sample_user.telegram_user_id
        assert entry.session_id == sample_session.id

    @pytest.mark.asyncio
    async def test_add_cgm_entry(self, test_db, sample_user, sample_session):
        repo = SessionRepository(test_db)
        entry = await repo.add_cgm_entry(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            file_path="users/100/sessions/s1/cgm_001.jpg",
            telegram_file_id="tg_cgm_001",
            timing_label="1 hour after",
        )
        assert entry.timing_label == "1 hour after"
        assert entry.user_id == sample_user.telegram_user_id

    @pytest.mark.asyncio
    async def test_add_activity_entry(self, test_db, sample_user, sample_session):
        repo = SessionRepository(test_db)
        entry = await repo.add_activity_entry(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            description="ran 2km",
        )
        assert entry.description == "ran 2km"
        assert entry.user_id == sample_user.telegram_user_id

    @pytest.mark.asyncio
    async def test_complete_session(self, test_db, sample_user, sample_session):
        repo = SessionRepository(test_db)
        completed = await repo.complete_session(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
        )
        assert completed.status == SessionStatus.COMPLETED
        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_expire_session(self, test_db, sample_user, sample_session):
        repo = SessionRepository(test_db)
        expired = await repo.expire_session(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
        )
        assert expired.status == SessionStatus.EXPIRED
        assert expired.expired_at is not None

    @pytest.mark.asyncio
    async def test_food_entry_user_id_must_match_session(self, test_db, sample_user, sample_session):
        """Cannot add entry to another user's session — Constitution II."""
        repo = SessionRepository(test_db)
        with pytest.raises(Exception):
            await repo.add_food_entry(
                user_id=999,  # wrong user
                session_id=sample_session.id,
                file_path="x",
                telegram_file_id="y",
            )

    @pytest.mark.asyncio
    async def test_get_entry_counts(self, test_db, sample_user, sample_session):
        repo = SessionRepository(test_db)
        await repo.add_food_entry(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            file_path="p",
            telegram_file_id="t",
        )
        await repo.add_cgm_entry(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            file_path="p2",
            telegram_file_id="t2",
            timing_label="before",
        )
        counts = await repo.get_entry_counts(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
        )
        assert counts["food"] == 1
        assert counts["cgm"] == 1
        assert counts["activity"] == 0
