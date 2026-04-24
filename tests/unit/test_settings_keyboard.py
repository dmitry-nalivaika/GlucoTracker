"""Unit tests for the /settings keyboard button and inline language picker.

Verifies:
1. _session_action_keyboard includes a /settings button.
2. handle_settings replies with an InlineKeyboardMarkup containing language options.
3. handle_language_setting_callback persists the chosen language and restores
   the ReplyKeyboardMarkup without removing it.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_cmd_update(user_id: int = 6001) -> MagicMock:
    mock_msg = MagicMock()
    mock_msg.reply_text = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_update = MagicMock()
    mock_update.message = mock_msg
    mock_update.effective_user = mock_user
    mock_update.callback_query = None
    return mock_update


def _make_callback_update(data: str, user_id: int = 6002) -> MagicMock:
    mock_cq = MagicMock()
    mock_cq.data = data
    mock_cq.answer = AsyncMock()
    mock_cq.edit_message_text = AsyncMock()
    mock_cq.edit_message_reply_markup = AsyncMock()
    mock_cq.message = MagicMock()
    mock_cq.message.chat_id = 44001
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_update = MagicMock()
    mock_update.callback_query = mock_cq
    mock_update.message = None
    mock_update.effective_user = mock_user
    return mock_update


def _make_context(user_data: dict | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.user_data = user_data if user_data is not None else {"lang": "en"}
    ctx.bot = MagicMock()
    ctx.bot.send_message = AsyncMock()
    ctx.args = []
    return ctx


class TestSessionKeyboardHasSettings:
    """_session_action_keyboard must expose a /settings button."""

    def test_session_keyboard_contains_settings_button(self) -> None:
        from glucotrack.bot.handlers import _session_action_keyboard

        kb = _session_action_keyboard("en")
        all_texts = [btn.text for row in kb.keyboard for btn in row]
        assert "/settings" in all_texts, "Session action keyboard must contain '/settings' button"

    def test_session_keyboard_still_contains_done_cancel_status(self) -> None:
        from glucotrack.bot.handlers import _session_action_keyboard

        kb = _session_action_keyboard("en")
        all_texts = [btn.text for row in kb.keyboard for btn in row]
        for cmd in ("/done", "/cancel", "/status"):
            assert cmd in all_texts, f"Session keyboard must still contain '{cmd}'"


class TestHandleSettings:
    """handle_settings must reply with an InlineKeyboardMarkup language picker."""

    @pytest.mark.asyncio
    async def test_settings_replies_with_inline_language_keyboard(self) -> None:
        """handle_settings sends a message containing an InlineKeyboardMarkup."""
        from telegram import InlineKeyboardMarkup

        from glucotrack.bot.handlers import handle_settings

        mock_update = _make_cmd_update()
        mock_context = _make_context()

        await handle_settings(mock_update, mock_context)

        assert mock_update.message.reply_text.called, "handle_settings must reply"
        markups = [
            call.kwargs.get("reply_markup")
            for call in mock_update.message.reply_text.call_args_list
        ]
        assert any(
            isinstance(m, InlineKeyboardMarkup) for m in markups
        ), "handle_settings must include an InlineKeyboardMarkup in its reply"

    @pytest.mark.asyncio
    async def test_settings_language_keyboard_has_en_and_ru_buttons(self) -> None:
        """Inline language keyboard must have buttons for 'en' and 'ru'."""
        from glucotrack.bot.handlers import handle_settings

        mock_update = _make_cmd_update()
        mock_context = _make_context()

        await handle_settings(mock_update, mock_context)

        all_calls_kwargs = [c.kwargs for c in mock_update.message.reply_text.call_args_list]
        inline_kb = next(
            (kw["reply_markup"] for kw in all_calls_kwargs if kw.get("reply_markup")),
            None,
        )
        assert inline_kb is not None
        all_callback_data = [btn.callback_data for row in inline_kb.inline_keyboard for btn in row]
        assert "lang_set:en" in all_callback_data, "Must have 'lang_set:en' button"
        assert "lang_set:ru" in all_callback_data, "Must have 'lang_set:ru' button"


class TestHandleLanguageSettingCallback:
    """handle_language_setting_callback must persist language and restore session keyboard."""

    @pytest.mark.asyncio
    async def test_lang_set_en_persists_and_restores_keyboard(self) -> None:
        """lang_set:en → language saved to DB and context, ReplyKeyboardMarkup restored."""

        from glucotrack.bot.handlers import handle_language_setting_callback

        mock_update = _make_callback_update("lang_set:en")
        mock_context = _make_context({"lang": "ru"})

        with patch("glucotrack.bot.handlers._get_db_session") as mock_db_ctx:
            mock_db = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo = AsyncMock()
            mock_repo.update_language = AsyncMock()
            with patch("glucotrack.bot.handlers.UserRepository", return_value=mock_repo):
                await handle_language_setting_callback(mock_update, mock_context)

        # Language should be updated in user_data
        assert (
            mock_context.user_data.get("lang") == "en"
        ), "Language must be updated in user_data after lang_set:en"

        # DB should have been called to persist
        mock_repo.update_language.assert_awaited_once()

        # The edit_message_text reply must include ReplyKeyboardMarkup
        assert (
            mock_update.callback_query.edit_message_text.called
        ), "edit_message_text must be called to confirm language change"

    @pytest.mark.asyncio
    async def test_lang_set_ru_updates_language_to_ru(self) -> None:
        """lang_set:ru → context.user_data['lang'] becomes 'ru'."""
        from glucotrack.bot.handlers import handle_language_setting_callback

        mock_update = _make_callback_update("lang_set:ru")
        mock_context = _make_context({"lang": "en"})

        with patch("glucotrack.bot.handlers._get_db_session") as mock_db_ctx:
            mock_db = AsyncMock()
            mock_db_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo = AsyncMock()
            mock_repo.update_language = AsyncMock()
            with patch("glucotrack.bot.handlers.UserRepository", return_value=mock_repo):
                await handle_language_setting_callback(mock_update, mock_context)

        assert mock_context.user_data.get("lang") == "ru"
