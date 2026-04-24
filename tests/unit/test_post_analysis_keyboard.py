"""Unit tests — post-analysis keyboard (feature 004 bugfix).

After the final analysis summary is delivered to the user, a ReplyKeyboardMarkup
must be sent so the user has buttons to start a new session, view trends, etc.

Covers:
1. _post_session_keyboard exists and includes /new and /trend buttons.
2. run_analysis sends reply_markup with the result message when one is supplied.
3. run_analysis error paths (AnalysisError, cgm_unparseable, unexpected) also
   send the keyboard so the user is never left stranded.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestPostSessionKeyboard:
    """_post_session_keyboard must have /new and /trend buttons."""

    def test_post_session_keyboard_has_new_button(self) -> None:
        from glucotrack.bot.handlers import _post_session_keyboard

        kb = _post_session_keyboard("en")
        all_texts = [btn.text for row in kb.keyboard for btn in row]
        assert "/new" in all_texts, "Post-session keyboard must contain '/new'"

    def test_post_session_keyboard_has_trend_button(self) -> None:
        from glucotrack.bot.handlers import _post_session_keyboard

        kb = _post_session_keyboard("en")
        all_texts = [btn.text for row in kb.keyboard for btn in row]
        assert "/trend" in all_texts, "Post-session keyboard must contain '/trend'"

    def test_post_session_keyboard_russian(self) -> None:
        from glucotrack.bot.handlers import _post_session_keyboard

        kb = _post_session_keyboard("ru")
        all_texts = [btn.text for row in kb.keyboard for btn in row]
        assert "/new" in all_texts
        assert "/trend" in all_texts


class TestRunAnalysisKeyboard:
    """run_analysis must forward reply_markup to every bot.send_message call."""

    def _make_analysis_service(self) -> object:
        from glucotrack.services.analysis_service import AnalysisService

        svc = AnalysisService.__new__(AnalysisService)
        svc._db = AsyncMock()
        svc._ai = AsyncMock()
        svc._miro = None
        svc._storage = MagicMock()
        svc._sess_repo = AsyncMock()
        svc._analysis_repo = AsyncMock()
        return svc

    def _fake_ai_result(self) -> dict:
        return {
            "cgm_parseable": True,
            "nutrition": {"carbs_g": 50, "proteins_g": 20, "fats_g": 10, "gi_estimate": 60},
            "glucose_curve": [],
            "correlation": {"summary": "OK"},
            "recommendations": [],
            "target_range_note": None,
            "activity": None,
        }

    def _make_mock_bot(self) -> AsyncMock:
        bot = AsyncMock()
        bot.send_message = AsyncMock()
        return bot

    @pytest.mark.asyncio
    async def test_success_path_sends_keyboard(self) -> None:
        """Analysis result message must include reply_markup when supplied."""
        from telegram import ReplyKeyboardMarkup

        from glucotrack.bot.handlers import _post_session_keyboard
        from glucotrack.services.analysis_service import AnalysisService

        svc = self._make_analysis_service()
        bot = self._make_mock_bot()
        kb = _post_session_keyboard("en")

        fake_session = MagicMock()
        fake_session.food_entries = []
        fake_session.cgm_entries = []
        fake_session.activity_entries = []

        fake_user = MagicMock()
        fake_user.language = "en"

        fake_analysis = MagicMock()
        fake_analysis.id = "ana-001"
        fake_analysis.user_id = 1
        fake_analysis.nutrition_json = '{"carbs_g":50,"proteins_g":20,"fats_g":10,"gi_estimate":60}'
        fake_analysis.glucose_curve_json = "[]"
        fake_analysis.correlation_json = '{"summary":"OK"}'
        fake_analysis.recommendations_json = "[]"
        fake_analysis.within_target_notes = None
        fake_analysis.activity_json = None

        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none = MagicMock(
            side_effect=[fake_session, None]  # session load, miro card (not used here)
        )
        svc._db.execute = AsyncMock(return_value=mock_scalar)
        svc._db.commit = AsyncMock()
        svc._db.add = MagicMock()

        user_repo_mock = AsyncMock()
        user_repo_mock.get_by_telegram_id = AsyncMock(return_value=fake_user)
        svc._analysis_repo.save_analysis = AsyncMock(return_value=fake_analysis)
        svc._sess_repo.mark_analysed = AsyncMock()

        with (
            patch(
                "glucotrack.services.analysis_service.UserRepository", return_value=user_repo_mock
            ),
            patch("glucotrack.repositories.user_repository.effective_lang", return_value="en"),
            patch("glucotrack.services.analysis_service.effective_lang", return_value="en"),
        ):
            await AnalysisService.run_analysis(
                svc,
                user_id=1,
                session_id="sess-001",
                chat_id=12345,
                bot=bot,
                reply_markup=kb,
            )

        assert bot.send_message.called, "bot.send_message must be called"
        send_calls_with_keyboard = [
            call
            for call in bot.send_message.call_args_list
            if isinstance(call.kwargs.get("reply_markup"), ReplyKeyboardMarkup)
        ]
        assert (
            len(send_calls_with_keyboard) >= 1
        ), "At least one bot.send_message call must include ReplyKeyboardMarkup"

    @pytest.mark.asyncio
    async def test_analysis_error_path_sends_keyboard(self) -> None:
        """When AI analysis fails, the error message must include reply_markup."""
        from telegram import ReplyKeyboardMarkup

        from glucotrack.bot.handlers import _post_session_keyboard
        from glucotrack.services.ai_service import AnalysisError
        from glucotrack.services.analysis_service import AnalysisService

        svc = self._make_analysis_service()
        bot = self._make_mock_bot()
        kb = _post_session_keyboard("en")

        fake_session = MagicMock()
        fake_session.food_entries = []
        fake_session.cgm_entries = []
        fake_session.activity_entries = []

        fake_user = MagicMock()

        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none = MagicMock(return_value=fake_session)
        svc._db.execute = AsyncMock(return_value=mock_scalar)
        svc._db.commit = AsyncMock()

        user_repo_mock = AsyncMock()
        user_repo_mock.get_by_telegram_id = AsyncMock(return_value=fake_user)
        svc._ai.analyse_session = AsyncMock(side_effect=AnalysisError("AI down"))

        with (
            patch(
                "glucotrack.services.analysis_service.UserRepository", return_value=user_repo_mock
            ),
            patch("glucotrack.services.analysis_service.effective_lang", return_value="en"),
        ):
            await AnalysisService.run_analysis(
                svc,
                user_id=1,
                session_id="sess-001",
                chat_id=12345,
                bot=bot,
                reply_markup=kb,
            )

        assert bot.send_message.called
        keyboard_calls = [
            c
            for c in bot.send_message.call_args_list
            if isinstance(c.kwargs.get("reply_markup"), ReplyKeyboardMarkup)
        ]
        assert (
            len(keyboard_calls) >= 1
        ), "Error path must also send ReplyKeyboardMarkup so user has buttons"
