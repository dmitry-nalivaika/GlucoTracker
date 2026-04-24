"""Unit tests for flat photo classification keyboard (feature 004 UX improvement).

Verifies that:
1. _photo_type_keyboard shows all options at once: Food + 4 CGM timing variants.
2. No intermediate "type:cgm" nesting button remains.
3. handle_photo_type_callback with a flat CGM callback saves directly (no CGM_TIMING_PROMPT).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_flat_callback_update(data: str, user_id: int = 9001) -> MagicMock:
    """Build an Update mock simulating an inline button click."""
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


def _make_context_with_pending(user_id: int = 9001) -> MagicMock:
    ctx = MagicMock()
    ctx.user_data = {
        "lang": "en",
        "pending_file_id": "fake_file_id",
        "pending_file_bytes": b"fakebytes",
    }
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


class TestFlatPhotoKeyboardStructure:
    """_photo_type_keyboard must be a flat single-step keyboard."""

    def test_flat_keyboard_contains_food_button(self) -> None:
        """Food button with callback_data 'type:food' must be present."""
        from telegram import InlineKeyboardButton

        from glucotrack.bot.handlers import _photo_type_keyboard

        kb = _photo_type_keyboard("en")
        all_buttons: list[InlineKeyboardButton] = [btn for row in kb.inline_keyboard for btn in row]
        data_values = [b.callback_data for b in all_buttons]
        assert "type:food" in data_values, "Expected 'type:food' button in flat keyboard"

    def test_flat_keyboard_contains_all_cgm_timing_buttons(self) -> None:
        """All 4 CGM timing buttons must be present in the flat keyboard."""
        from glucotrack.bot.handlers import _photo_type_keyboard

        kb = _photo_type_keyboard("en")
        all_data = {btn.callback_data for row in kb.inline_keyboard for btn in row}

        expected_prefixes = {
            "flat:before eating",
            "flat:right after eating",
            "flat:1 hour after",
            "flat:2 hours after",
        }
        missing = expected_prefixes - all_data
        assert not missing, f"Missing flat CGM timing buttons: {missing}"

    def test_flat_keyboard_has_no_type_cgm_nesting_button(self) -> None:
        """There must be NO 'type:cgm' button — that was the nesting button."""
        from glucotrack.bot.handlers import _photo_type_keyboard

        kb = _photo_type_keyboard("en")
        all_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert (
            "type:cgm" not in all_data
        ), "Flat keyboard must NOT contain 'type:cgm' nesting button"

    def test_flat_keyboard_total_button_count(self) -> None:
        """Keyboard must have at least 5 buttons (Food + 4 CGM timings)."""
        from glucotrack.bot.handlers import _photo_type_keyboard

        kb = _photo_type_keyboard("en")
        total = sum(len(row) for row in kb.inline_keyboard)
        assert total >= 5, f"Expected ≥5 buttons in flat keyboard, got {total}"

    def test_flat_keyboard_russian_locale(self) -> None:
        """Keyboard structure (callback_data) must be identical for Russian."""
        from glucotrack.bot.handlers import _photo_type_keyboard

        kb = _photo_type_keyboard("ru")
        all_data = {btn.callback_data for row in kb.inline_keyboard for btn in row}
        assert "flat:before eating" in all_data
        assert "flat:1 hour after" in all_data


class TestFlatPhotoTypeCallback:
    """handle_photo_type_callback must directly save CGM for flat: callbacks."""

    @pytest.mark.asyncio
    async def test_flat_before_eating_saves_cgm_returns_session_open(self) -> None:
        """flat:before eating → _save_cgm called, returns SESSION_OPEN (not CGM_TIMING_PROMPT)."""
        from glucotrack.bot.handlers import SESSION_OPEN, handle_photo_type_callback

        mock_update = _make_flat_callback_update("flat:before eating")
        mock_context = _make_context_with_pending()

        fake_service = AsyncMock()
        fake_service.handle_photo = AsyncMock()

        with patch(
            "glucotrack.bot.handlers._session_service",
            new=_fake_session_service_ctx(fake_service),
        ):
            result = await handle_photo_type_callback(mock_update, mock_context)

        assert result == SESSION_OPEN, f"Expected SESSION_OPEN ({SESSION_OPEN}), got {result}"

    @pytest.mark.asyncio
    async def test_flat_1h_after_saves_cgm_with_correct_timing_label(self) -> None:
        """flat:1 hour after → handle_photo saves CGM with timing_label='1 hour after'."""
        from glucotrack.bot.handlers import handle_photo_type_callback

        mock_update = _make_flat_callback_update("flat:1 hour after")
        mock_context = _make_context_with_pending()

        fake_service = AsyncMock()
        fake_service.handle_photo = AsyncMock()

        with patch(
            "glucotrack.bot.handlers._session_service",
            new=_fake_session_service_ctx(fake_service),
        ):
            await handle_photo_type_callback(mock_update, mock_context)

        fake_service.handle_photo.assert_awaited_once()
        _, kwargs = fake_service.handle_photo.call_args
        assert (
            kwargs.get("timing_label") == "1 hour after"
        ), f"Expected timing_label='1 hour after', got {kwargs.get('timing_label')}"

    @pytest.mark.asyncio
    async def test_flat_cgm_does_not_transition_to_cgm_timing_prompt(self) -> None:
        """flat: callback must NOT return CGM_TIMING_PROMPT state."""
        from glucotrack.bot.handlers import CGM_TIMING_PROMPT, handle_photo_type_callback

        for flat_data in (
            "flat:before eating",
            "flat:right after eating",
            "flat:1 hour after",
            "flat:2 hours after",
        ):
            mock_update = _make_flat_callback_update(flat_data)
            mock_context = _make_context_with_pending()

            fake_service = AsyncMock()
            fake_service.handle_photo = AsyncMock()

            with patch(
                "glucotrack.bot.handlers._session_service",
                new=_fake_session_service_ctx(fake_service),
            ):
                result = await handle_photo_type_callback(mock_update, mock_context)

            assert (
                result != CGM_TIMING_PROMPT
            ), f"Flat callback '{flat_data}' must NOT return CGM_TIMING_PROMPT"

    @pytest.mark.asyncio
    async def test_flat_cgm_callback_restores_session_keyboard(self) -> None:
        """After flat CGM click, context.bot.send_message must include ReplyKeyboardMarkup."""
        from telegram import ReplyKeyboardMarkup

        from glucotrack.bot.handlers import handle_photo_type_callback

        mock_update = _make_flat_callback_update("flat:2 hours after")
        mock_context = _make_context_with_pending()

        fake_service = AsyncMock()
        fake_service.handle_photo = AsyncMock()

        with patch(
            "glucotrack.bot.handlers._session_service",
            new=_fake_session_service_ctx(fake_service),
        ):
            await handle_photo_type_callback(mock_update, mock_context)

        assert (
            mock_context.bot.send_message.called
        ), "context.bot.send_message must be called to restore session keyboard"
        send_kwargs = mock_context.bot.send_message.call_args.kwargs
        assert isinstance(
            send_kwargs.get("reply_markup"), ReplyKeyboardMarkup
        ), f"Expected ReplyKeyboardMarkup, got {send_kwargs.get('reply_markup')}"
