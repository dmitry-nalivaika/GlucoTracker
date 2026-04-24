"""Unit tests — keyboard persistence after activity submission (feature 004 bugfix).

Verifies that handle_activity_text ALWAYS restores ReplyKeyboardMarkup:
  - success path: keyboard included in ack message
  - error path (service raises): keyboard included in generic-error message

Also verifies handle_photo_type_callback food/unsure paths send a new message
with ReplyKeyboardMarkup so the keyboard is always explicitly restored.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_text_update(text: str, user_id: int = 7777) -> MagicMock:
    mock_msg = MagicMock()
    mock_msg.reply_text = AsyncMock()
    mock_msg.text = text
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_update = MagicMock()
    mock_update.message = mock_msg
    mock_update.effective_user = mock_user
    mock_update.callback_query = None
    return mock_update


def _make_callback_update(data: str, user_id: int = 7778) -> MagicMock:
    mock_cq = MagicMock()
    mock_cq.data = data
    mock_cq.answer = AsyncMock()
    mock_cq.edit_message_text = AsyncMock()
    mock_cq.edit_message_reply_markup = AsyncMock()
    mock_cq.message = MagicMock()
    mock_cq.message.chat_id = 55099
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
    ctx.bot.get_file = AsyncMock()
    fake_file = AsyncMock()
    fake_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fakebytes"))
    ctx.bot.get_file.return_value = fake_file
    return ctx


def _fake_session_service_ctx(service: MagicMock):
    @asynccontextmanager
    async def _ctx(_context):
        yield service

    return _ctx


class TestActivityTextKeyboard:
    """handle_activity_text must ALWAYS include ReplyKeyboardMarkup in its reply."""

    @pytest.mark.asyncio
    async def test_success_path_sends_keyboard(self) -> None:
        """Activity ack (success) must include ReplyKeyboardMarkup."""
        from telegram import ReplyKeyboardMarkup

        from glucotrack.bot.handlers import handle_activity_text

        mock_update = _make_text_update("went for a 30 min walk")
        mock_context = _make_context()

        fake_service = AsyncMock()
        fake_service.handle_activity = AsyncMock()

        with patch(
            "glucotrack.bot.handlers._session_service",
            new=_fake_session_service_ctx(fake_service),
        ):
            await handle_activity_text(mock_update, mock_context)

        all_markups = [
            call.kwargs.get("reply_markup")
            for call in mock_update.message.reply_text.call_args_list
        ]
        assert any(
            isinstance(m, ReplyKeyboardMarkup) for m in all_markups
        ), "Success path must reply with ReplyKeyboardMarkup"

    @pytest.mark.asyncio
    async def test_error_path_sends_keyboard(self) -> None:
        """When service raises, the error message must STILL include ReplyKeyboardMarkup."""
        from telegram import ReplyKeyboardMarkup

        from glucotrack.bot.handlers import handle_activity_text

        mock_update = _make_text_update("some activity text")
        mock_context = _make_context()

        fake_service = AsyncMock()
        fake_service.handle_activity = AsyncMock(side_effect=RuntimeError("db error"))

        with patch(
            "glucotrack.bot.handlers._session_service",
            new=_fake_session_service_ctx(fake_service),
        ):
            await handle_activity_text(mock_update, mock_context)

        all_markups = [
            call.kwargs.get("reply_markup")
            for call in mock_update.message.reply_text.call_args_list
        ]
        assert any(isinstance(m, ReplyKeyboardMarkup) for m in all_markups), (
            "Error path must ALSO reply with ReplyKeyboardMarkup — "
            "sending without it causes keyboard to disappear"
        )
        from telegram import ReplyKeyboardRemove

        assert not any(
            isinstance(m, ReplyKeyboardRemove) for m in all_markups
        ), "Error path must NOT send ReplyKeyboardRemove"


class TestFoodCallbackKeyboard:
    """handle_photo_type_callback food/unsure paths must restore ReplyKeyboardMarkup."""

    @pytest.mark.asyncio
    async def test_food_callback_restores_session_keyboard(self) -> None:
        """After food photo classification, context.bot.send_message must include
        ReplyKeyboardMarkup to restore the session keyboard."""
        from telegram import ReplyKeyboardMarkup

        from glucotrack.bot.handlers import handle_photo_type_callback

        mock_update = _make_callback_update("type:food")
        mock_context = _make_context(
            {"lang": "en", "pending_file_id": "fid", "pending_file_bytes": b"bytes"}
        )

        fake_service = AsyncMock()
        fake_service.handle_photo = AsyncMock()

        with patch(
            "glucotrack.bot.handlers._session_service",
            new=_fake_session_service_ctx(fake_service),
        ):
            await handle_photo_type_callback(mock_update, mock_context)

        assert mock_context.bot.send_message.called, (
            "context.bot.send_message must be called after food classification "
            "to restore the session keyboard"
        )
        send_kwargs = mock_context.bot.send_message.call_args.kwargs
        assert isinstance(send_kwargs.get("reply_markup"), ReplyKeyboardMarkup), (
            f"Expected ReplyKeyboardMarkup in send_message, got "
            f"{send_kwargs.get('reply_markup')}"
        )

    @pytest.mark.asyncio
    async def test_unsure_callback_restores_session_keyboard(self) -> None:
        """After 'not sure' classification, ReplyKeyboardMarkup must be restored."""
        from telegram import ReplyKeyboardMarkup

        from glucotrack.bot.handlers import handle_photo_type_callback

        mock_update = _make_callback_update("type:unsure")
        mock_context = _make_context(
            {"lang": "en", "pending_file_id": "fid", "pending_file_bytes": b"bytes"}
        )

        fake_service = AsyncMock()
        fake_service.handle_photo = AsyncMock()

        with patch(
            "glucotrack.bot.handlers._session_service",
            new=_fake_session_service_ctx(fake_service),
        ):
            await handle_photo_type_callback(mock_update, mock_context)

        assert (
            mock_context.bot.send_message.called
        ), "context.bot.send_message must be called after 'not sure' classification"
        send_kwargs = mock_context.bot.send_message.call_args.kwargs
        assert isinstance(
            send_kwargs.get("reply_markup"), ReplyKeyboardMarkup
        ), f"Expected ReplyKeyboardMarkup, got {send_kwargs.get('reply_markup')}"
