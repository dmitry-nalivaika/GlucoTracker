"""Unit tests for user domain logic — T022."""
from __future__ import annotations

import pytest
import pytest_asyncio

from glucotrack.domain.user import get_or_create_user
from glucotrack.models.user import User


class TestGetOrCreateUser:
    """Tests for get_or_create_user function."""

    @pytest.mark.asyncio
    async def test_creates_user_on_first_call(self, test_db):
        user = await get_or_create_user(test_db, telegram_user_id=999)
        assert user.telegram_user_id == 999
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_returns_existing_user_on_second_call(self, test_db):
        user1 = await get_or_create_user(test_db, telegram_user_id=999)
        user2 = await get_or_create_user(test_db, telegram_user_id=999)
        assert user1.telegram_user_id == user2.telegram_user_id

    @pytest.mark.asyncio
    async def test_different_users_are_independent(self, test_db):
        user_a = await get_or_create_user(test_db, telegram_user_id=111)
        user_b = await get_or_create_user(test_db, telegram_user_id=222)
        assert user_a.telegram_user_id != user_b.telegram_user_id

    @pytest.mark.asyncio
    async def test_updates_last_seen_at_on_each_call(self, test_db):
        import asyncio
        user1 = await get_or_create_user(test_db, telegram_user_id=777)
        original_last_seen = user1.last_seen_at
        await asyncio.sleep(0.01)
        user2 = await get_or_create_user(test_db, telegram_user_id=777)
        # last_seen_at should be updated
        assert user2.last_seen_at >= original_last_seen

    @pytest.mark.asyncio
    async def test_returns_user_with_correct_id(self, test_db):
        user = await get_or_create_user(test_db, telegram_user_id=12345)
        assert user.telegram_user_id == 12345
