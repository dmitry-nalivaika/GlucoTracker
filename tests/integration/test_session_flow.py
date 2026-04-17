"""Integration tests for US1 full session logging flow — T024."""
from __future__ import annotations

import os
import tempfile

import pytest

from glucotrack.domain.user import get_or_create_user
from glucotrack.models.session import SessionStatus
from glucotrack.repositories.session_repository import SessionRepository
from glucotrack.repositories.user_repository import UserRepository
from glucotrack.storage.local_storage import StorageRepository


class TestSessionFlow:
    """Full US1 flow: open session → add entries → complete → verify DB + storage."""

    @pytest.mark.asyncio
    async def test_full_session_logging_flow(self, test_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageRepository(tmpdir)
            user_repo = UserRepository(test_db)
            sess_repo = SessionRepository(test_db)

            # 1. User opens (or gets) a session
            user = await get_or_create_user(test_db, telegram_user_id=42)
            session = await sess_repo.create_session(user_id=user.telegram_user_id)
            assert session.status == SessionStatus.OPEN

            # 2. Add food entry with file
            food_path = storage.save_file(user.telegram_user_id, session.id, "food_001.jpg", b"img")
            food = await sess_repo.add_food_entry(
                user_id=user.telegram_user_id,
                session_id=session.id,
                file_path=food_path,
                telegram_file_id="tg_f001",
                description="pasta",
            )
            assert food.user_id == user.telegram_user_id

            # 3. Add CGM screenshot
            cgm_path = storage.save_file(user.telegram_user_id, session.id, "cgm_001.jpg", b"cgm")
            cgm = await sess_repo.add_cgm_entry(
                user_id=user.telegram_user_id,
                session_id=session.id,
                file_path=cgm_path,
                telegram_file_id="tg_c001",
                timing_label="1 hour after",
            )
            assert cgm.user_id == user.telegram_user_id

            # 4. Add activity
            act = await sess_repo.add_activity_entry(
                user_id=user.telegram_user_id,
                session_id=session.id,
                description="walked 30 min",
            )
            assert act.user_id == user.telegram_user_id

            # 5. Complete session
            completed = await sess_repo.complete_session(
                user_id=user.telegram_user_id, session_id=session.id
            )
            assert completed.status == SessionStatus.COMPLETED
            assert completed.completed_at is not None

            # 6. Verify entry counts
            counts = await sess_repo.get_entry_counts(
                user_id=user.telegram_user_id, session_id=session.id
            )
            assert counts["food"] == 1
            assert counts["cgm"] == 1
            assert counts["activity"] == 1

            # 7. Verify storage paths follow Constitution II pattern
            assert "42" in food_path
            assert session.id in food_path
            assert storage.file_exists(food_path)

    @pytest.mark.asyncio
    async def test_cross_user_data_isolation(self, test_db):
        """User A's session is invisible to User B — SC-006."""
        user_repo = UserRepository(test_db)
        sess_repo = SessionRepository(test_db)

        user_a = await get_or_create_user(test_db, telegram_user_id=1001)
        user_b = await get_or_create_user(test_db, telegram_user_id=1002)

        await sess_repo.create_session(user_id=user_a.telegram_user_id)

        # User B should see no open session
        b_session = await sess_repo.get_open_session(user_id=user_b.telegram_user_id)
        assert b_session is None

    @pytest.mark.asyncio
    async def test_session_accepts_inputs_in_any_order(self, test_db):
        """Inputs accepted regardless of order (spec edge case)."""
        user_repo = UserRepository(test_db)
        sess_repo = SessionRepository(test_db)
        user = await get_or_create_user(test_db, telegram_user_id=55)
        session = await sess_repo.create_session(user_id=user.telegram_user_id)

        # Activity first, then food, then CGM
        await sess_repo.add_activity_entry(
            user_id=user.telegram_user_id, session_id=session.id, description="ran 1km"
        )
        await sess_repo.add_food_entry(
            user_id=user.telegram_user_id,
            session_id=session.id,
            file_path="p",
            telegram_file_id="t1",
        )
        await sess_repo.add_cgm_entry(
            user_id=user.telegram_user_id,
            session_id=session.id,
            file_path="p2",
            telegram_file_id="t2",
            timing_label="before",
        )
        counts = await sess_repo.get_entry_counts(
            user_id=user.telegram_user_id, session_id=session.id
        )
        assert counts["food"] == 1
        assert counts["cgm"] == 1
        assert counts["activity"] == 1

    @pytest.mark.asyncio
    async def test_multiple_food_photos_all_saved(self, test_db):
        """Multiple food photos in one session are all retained (spec edge case)."""
        user_repo = UserRepository(test_db)
        sess_repo = SessionRepository(test_db)
        user = await get_or_create_user(test_db, telegram_user_id=77)
        session = await sess_repo.create_session(user_id=user.telegram_user_id)

        for i in range(3):
            await sess_repo.add_food_entry(
                user_id=user.telegram_user_id,
                session_id=session.id,
                file_path=f"p{i}",
                telegram_file_id=f"tg{i}",
            )
        counts = await sess_repo.get_entry_counts(
            user_id=user.telegram_user_id, session_id=session.id
        )
        assert counts["food"] == 3
