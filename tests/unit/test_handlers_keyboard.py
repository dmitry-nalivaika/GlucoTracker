"""Unit tests for persistent session action keyboard (feature 004 bugfix).

Verifies that handle_disambiguate and _save_cgm restore the ReplyKeyboardMarkup
instead of removing it — the root cause of keyboards disappearing mid-session.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_context(user_data: dict | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.user_data = user_data if user_data is not None else {"lang": "en"}
    ctx.bot = MagicMock()
    ctx.bot.send_message = AsyncMock()
    return ctx


def _make_message_update(text: str, user_id: int = 8001) -> MagicMock:
    mock_msg = MagicMock()
    mock_msg.reply_text = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_update = MagicMock()
    mock_update.message = mock_msg
    mock_update.message.text = text
    mock_update.effective_user = mock_user
    mock_update.callback_query = None
    return mock_update


def _fake_session_service_ctx(service: MagicMock):
    @asynccontextmanager
    async def _ctx(_context):
        yield service

    return _ctx


class TestDisambiguateKeyboard:
    """handle_disambiguate must restore the session keyboard in both branches."""

    @pytest.mark.asyncio
    async def test_new_session_branch_sends_keyboard_not_remove(self) -> None:
        """'Start new session' branch must reply with ReplyKeyboardMarkup, not Remove."""
        from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

        from glucotrack.bot.handlers import handle_disambiguate

        mock_update = _make_message_update("Start new session")
        mock_context = _make_context()

        fake_service = AsyncMock()
        fake_service.get_or_open_session = AsyncMock(return_value=(MagicMock(), True))

        with patch(
            "glucotrack.bot.handlers._session_service",
            new=_fake_session_service_ctx(fake_service),
        ):
            await handle_disambiguate(mock_update, mock_context)

        all_markups = [
            call.kwargs.get("reply_markup")
            for call in mock_update.message.reply_text.call_args_list
        ]
        assert any(
            isinstance(m, ReplyKeyboardMarkup) for m in all_markups
        ), "Expected at least one ReplyKeyboardMarkup call after 'new session' disambiguation"
        assert not any(
            isinstance(m, ReplyKeyboardRemove) for m in all_markups
        ), "Must NOT send ReplyKeyboardRemove after 'new session' disambiguation"

    @pytest.mark.asyncio
    async def test_continue_session_branch_sends_keyboard_not_remove(self) -> None:
        """'Continue session' branch must reply with ReplyKeyboardMarkup, not Remove."""
        from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

        from glucotrack.bot.handlers import handle_disambiguate

        mock_update = _make_message_update("Continue")
        mock_context = _make_context()

        fake_service = AsyncMock()

        with patch(
            "glucotrack.bot.handlers._session_service",
            new=_fake_session_service_ctx(fake_service),
        ):
            await handle_disambiguate(mock_update, mock_context)

        all_markups = [
            call.kwargs.get("reply_markup")
            for call in mock_update.message.reply_text.call_args_list
        ]
        assert any(
            isinstance(m, ReplyKeyboardMarkup) for m in all_markups
        ), "Expected at least one ReplyKeyboardMarkup call after 'continue' disambiguation"
        assert not any(
            isinstance(m, ReplyKeyboardRemove) for m in all_markups
        ), "Must NOT send ReplyKeyboardRemove after 'continue' disambiguation"


class TestSaveCGMCallbackKeyboard:
    """_save_cgm callback_query path must restore the session keyboard."""

    @pytest.mark.asyncio
    async def test_cgm_callback_path_sends_keyboard_via_bot(self) -> None:
        """After CGM timing inline-button click, context.bot.send_message
        is called with reply_markup=ReplyKeyboardMarkup (restores session keyboard)."""
        from telegram import ReplyKeyboardMarkup

        from glucotrack.bot.handlers import _save_cgm

        # Build a callback_query update (no update.message)
        mock_cq = MagicMock()
        mock_cq.edit_message_reply_markup = AsyncMock()
        mock_cq.edit_message_text = AsyncMock()  # current code path (pre-fix)
        mock_cq.message = MagicMock()
        mock_cq.message.chat_id = 55001

        mock_user = MagicMock()
        mock_user.id = 8002

        mock_update = MagicMock()
        mock_update.callback_query = mock_cq
        mock_update.message = None
        mock_update.effective_user = mock_user

        mock_context = _make_context(
            {"lang": "en", "pending_file_bytes": b"cgm", "pending_file_id": "fid"}
        )

        fake_service = AsyncMock()
        fake_service.handle_photo = AsyncMock()

        with patch(
            "glucotrack.bot.handlers._session_service",
            new=_fake_session_service_ctx(fake_service),
        ):
            await _save_cgm(mock_update, mock_context, "1 hour after", lang="en")

        # context.bot.send_message should have been called with ReplyKeyboardMarkup
        assert (
            mock_context.bot.send_message.called
        ), "context.bot.send_message must be called to restore session keyboard"
        send_kwargs = mock_context.bot.send_message.call_args.kwargs
        assert isinstance(
            send_kwargs.get("reply_markup"), ReplyKeyboardMarkup
        ), f"Expected ReplyKeyboardMarkup in send_message, got {send_kwargs.get('reply_markup')}"
