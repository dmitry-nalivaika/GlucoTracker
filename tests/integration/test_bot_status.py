"""Integration tests for bot online/offline broadcast and handle_start (feature 004)."""

from __future__ import annotations

import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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


class TestHandleStartGuidedPrompt:
    """Tests for the guided prompt + keyboard sent from handle_start (BLOCKER AC1.1)."""

    def _make_update_and_context(self, user_id: int, chat_id: int, storage: object) -> tuple:
        """Build minimal PTB Update and context mocks."""
        mock_message = MagicMock()
        mock_message.reply_text = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.first_name = "Tester"
        mock_chat = MagicMock()
        mock_chat.id = chat_id
        mock_update = MagicMock()
        mock_update.effective_user = mock_user
        mock_update.message = mock_message
        mock_update.effective_chat = mock_chat

        settings = MagicMock()
        settings.session_idle_threshold_minutes = 60
        settings.session_idle_expiry_hours = 24
        mock_context = MagicMock()
        mock_context.user_data = {}
        mock_context.application.bot_data = {
            "settings": settings,
            "storage": storage,
        }
        return mock_update, mock_context

    @pytest.mark.asyncio
    async def test_start_with_no_session_sends_guided_prompt_and_keyboard(self, test_db) -> None:
        """AC1.1: /start with no open session sends guided prompt + ReplyKeyboardMarkup."""
        from telegram import ReplyKeyboardMarkup

        from glucotrack.bot.handlers import handle_start

        with tempfile.TemporaryDirectory() as tmpdir:
            from glucotrack.storage.local_storage import StorageRepository

            storage = StorageRepository(tmpdir)
            mock_update, mock_context = self._make_update_and_context(7001, 77001, storage)

            with patch("glucotrack.db.get_session") as mock_gs:
                mock_gs.return_value.__aenter__ = AsyncMock(return_value=test_db)
                mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
                await handle_start(mock_update, mock_context)

        reply_calls = mock_update.message.reply_text.call_args_list
        assert (
            len(reply_calls) == 2
        ), f"Expected 2 reply_text calls (welcome + guided prompt), got {len(reply_calls)}"
        second_kwargs = reply_calls[1].kwargs
        reply_markup = second_kwargs.get("reply_markup")
        assert reply_markup is not None, "Second message must include reply_markup"
        assert isinstance(
            reply_markup, ReplyKeyboardMarkup
        ), f"Expected ReplyKeyboardMarkup, got {type(reply_markup)}"

    @pytest.mark.asyncio
    async def test_start_with_existing_session_does_not_send_guided_prompt(self, test_db) -> None:
        """AC1.1: /start when user already has an open session sends only welcome (no keyboard)."""
        from glucotrack.bot.handlers import handle_start
        from glucotrack.domain.user import get_or_create_user
        from glucotrack.repositories.session_repository import SessionRepository

        # Pre-create an open session so handle_start finds an existing one
        await get_or_create_user(test_db, telegram_user_id=7002)
        await test_db.commit()
        sess_repo = SessionRepository(test_db)
        await sess_repo.create_session(user_id=7002)
        await test_db.commit()

        with tempfile.TemporaryDirectory() as tmpdir:
            from glucotrack.storage.local_storage import StorageRepository

            storage = StorageRepository(tmpdir)
            mock_update, mock_context = self._make_update_and_context(7002, 77002, storage)

            with patch("glucotrack.db.get_session") as mock_gs:
                mock_gs.return_value.__aenter__ = AsyncMock(return_value=test_db)
                mock_gs.return_value.__aexit__ = AsyncMock(return_value=False)
                await handle_start(mock_update, mock_context)

        reply_calls = mock_update.message.reply_text.call_args_list
        assert (
            len(reply_calls) == 1
        ), f"Expected 1 reply_text call (welcome only), got {len(reply_calls)}"
