"""Integration tests for bot online/offline broadcast (feature 004, US2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from glucotrack.bot import formatters


class TestBotOnlineBroadcast:
    """Tests for the online broadcast sent at bot startup."""

    @pytest.mark.asyncio
    async def test_online_broadcast_sends_to_all_users_with_chat_id(self, test_db) -> None:
        """Broadcast sends the online message to every user with a stored chat_id."""
        from glucotrack.bot.application import _broadcast_online
        from glucotrack.repositories.user_repository import UserRepository

        repo = UserRepository(test_db)
        u1 = await repo.create(telegram_user_id=9001)
        u2 = await repo.create(telegram_user_id=9002)
        await repo.create(telegram_user_id=9003)  # no chat_id — should NOT receive
        await repo.update_chat_id(u1.telegram_user_id, 88001)
        await repo.update_chat_id(u2.telegram_user_id, 88002)

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        with patch("glucotrack.db.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=test_db)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
            await _broadcast_online(mock_bot)

        # Should have sent to exactly the 2 users with chat_id
        sent_chat_ids = {call.kwargs["chat_id"] for call in mock_bot.send_message.call_args_list}
        assert 88001 in sent_chat_ids
        assert 88002 in sent_chat_ids
        assert len(sent_chat_ids) == 2

    @pytest.mark.asyncio
    async def test_online_broadcast_is_fire_and_forget_on_send_error(self, test_db) -> None:
        """A send error for one user must not abort the entire broadcast."""
        from glucotrack.bot.application import _broadcast_online
        from glucotrack.repositories.user_repository import UserRepository

        repo = UserRepository(test_db)
        u1 = await repo.create(telegram_user_id=9011)
        u2 = await repo.create(telegram_user_id=9012)
        await repo.update_chat_id(u1.telegram_user_id, 88011)
        await repo.update_chat_id(u2.telegram_user_id, 88012)

        mock_bot = AsyncMock()
        # First call raises, second should still succeed
        mock_bot.send_message = AsyncMock(side_effect=[Exception("network error"), None])

        with patch("glucotrack.db.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=test_db)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
            # Should not raise
            await _broadcast_online(mock_bot)

        assert mock_bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_online_broadcast_message_uses_user_language(self, test_db) -> None:
        """Online message is sent in the user's stored language."""
        from glucotrack.bot.application import _broadcast_online
        from glucotrack.repositories.user_repository import UserRepository

        repo = UserRepository(test_db)
        u = await repo.create(telegram_user_id=9021)
        await repo.update_language(u.telegram_user_id, "ru")
        await repo.update_chat_id(u.telegram_user_id, 88021)

        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        with patch("glucotrack.db.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=test_db)
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
            await _broadcast_online(mock_bot)

        assert mock_bot.send_message.call_count == 1
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 88021
        # Russian message contains Cyrillic
        text = call_kwargs["text"]
        assert any("\u0400" <= c <= "\u04ff" for c in text)
