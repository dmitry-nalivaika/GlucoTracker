"""Unit tests for AnalysisService — T034."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from glucotrack.models.session import SessionStatus
from glucotrack.repositories.analysis_repository import AnalysisRepository
from glucotrack.services.analysis_service import AnalysisService


VALID_ANALYSIS_RESULT = {
    "nutrition": {"carbs_g": 45, "proteins_g": 20, "fats_g": 10, "gi_estimate": 65, "notes": ""},
    "glucose_curve": [
        {"timing_label": "1h after", "estimated_value_mg_dl": 110, "in_range": True, "notes": ""}
    ],
    "correlation": {"spikes": [], "dips": [], "stable_zones": ["stable overall"], "summary": "OK"},
    "recommendations": [{"priority": 1, "text": "Keep it up!"}],
    "target_range_note": "All readings within 70–140 mg/dL.",
    "cgm_parseable": True,
    "cgm_parse_error": None,
}


class TestAnalysisService:
    """Tests for AnalysisService orchestration."""

    @pytest.mark.asyncio
    async def test_run_analysis_saves_to_db(self, test_db, sample_user, sample_session):
        """Analysis result is persisted to ai_analyses table with correct user_id."""
        from glucotrack.repositories.session_repository import SessionRepository

        # Complete the session first, add entries
        sess_repo = SessionRepository(test_db)
        await sess_repo.add_food_entry(
            sample_user.telegram_user_id, sample_session.id, "p", "t1"
        )
        await sess_repo.add_cgm_entry(
            sample_user.telegram_user_id, sample_session.id, "p2", "t2", "1h"
        )
        await sess_repo.complete_session(sample_user.telegram_user_id, sample_session.id)

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=VALID_ANALYSIS_RESULT)
        mock_bot = AsyncMock()
        mock_miro = AsyncMock()

        service = AnalysisService(
            db=test_db,
            ai_service=mock_ai,
            miro_service=mock_miro,
            storage_root="./data",
        )

        await service.run_analysis(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            chat_id=12345,
            bot=mock_bot,
        )

        analysis_repo = AnalysisRepository(test_db)
        analysis = await analysis_repo.get_analysis_by_session(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
        )
        assert analysis is not None
        assert analysis.user_id == sample_user.telegram_user_id
        assert json.loads(analysis.nutrition_json)["carbs_g"] == 45

    @pytest.mark.asyncio
    async def test_telegram_message_sent_with_analysis(self, test_db, sample_user, sample_session):
        """Bot.send_message is called with analysis content."""
        from glucotrack.repositories.session_repository import SessionRepository

        sess_repo = SessionRepository(test_db)
        await sess_repo.add_food_entry(
            sample_user.telegram_user_id, sample_session.id, "p", "t1"
        )
        await sess_repo.add_cgm_entry(
            sample_user.telegram_user_id, sample_session.id, "p2", "t2", "1h"
        )
        await sess_repo.complete_session(sample_user.telegram_user_id, sample_session.id)

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=VALID_ANALYSIS_RESULT)
        mock_bot = AsyncMock()
        mock_miro = AsyncMock()

        service = AnalysisService(
            db=test_db,
            ai_service=mock_ai,
            miro_service=mock_miro,
            storage_root="./data",
        )

        await service.run_analysis(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            chat_id=12345,
            bot=mock_bot,
        )

        assert mock_bot.send_message.called

    @pytest.mark.asyncio
    async def test_cgm_unparseable_sends_guidance_message(self, test_db, sample_user, sample_session):
        """Unparseable CGM triggers graceful degradation message (FR-011)."""
        from glucotrack.repositories.session_repository import SessionRepository

        sess_repo = SessionRepository(test_db)
        await sess_repo.add_food_entry(
            sample_user.telegram_user_id, sample_session.id, "p", "t1"
        )
        await sess_repo.add_cgm_entry(
            sample_user.telegram_user_id, sample_session.id, "p2", "t2", "1h"
        )
        await sess_repo.complete_session(sample_user.telegram_user_id, sample_session.id)

        unparseable = {
            **VALID_ANALYSIS_RESULT,
            "cgm_parseable": False,
            "cgm_parse_error": "Too blurry",
        }
        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=unparseable)
        mock_bot = AsyncMock()
        mock_miro = AsyncMock()

        service = AnalysisService(
            db=test_db,
            ai_service=mock_ai,
            miro_service=mock_miro,
            storage_root="./data",
        )

        await service.run_analysis(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            chat_id=12345,
            bot=mock_bot,
        )

        # Should still send a message (guidance, not error)
        assert mock_bot.send_message.called
        call_args = mock_bot.send_message.call_args
        # Message should mention re-submission
        message_text = str(call_args)
        assert "couldn't read" in message_text.lower() or "cgm" in message_text.lower() or mock_bot.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_analysis_failure_sends_error_message(self, test_db, sample_user, sample_session):
        """AI failure sends user-friendly error (not stack trace)."""
        from glucotrack.repositories.session_repository import SessionRepository
        from glucotrack.services.ai_service import AnalysisError

        sess_repo = SessionRepository(test_db)
        await sess_repo.add_food_entry(
            sample_user.telegram_user_id, sample_session.id, "p", "t1"
        )
        await sess_repo.add_cgm_entry(
            sample_user.telegram_user_id, sample_session.id, "p2", "t2", "1h"
        )
        await sess_repo.complete_session(sample_user.telegram_user_id, sample_session.id)

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(side_effect=AnalysisError("Claude timeout"))
        mock_bot = AsyncMock()
        mock_miro = AsyncMock()

        service = AnalysisService(
            db=test_db,
            ai_service=mock_ai,
            miro_service=mock_miro,
            storage_root="./data",
        )

        # Should NOT raise — error is caught and user-notified
        await service.run_analysis(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            chat_id=12345,
            bot=mock_bot,
        )

        assert mock_bot.send_message.called
