"""Integration tests for US2 analysis pipeline — T036."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from glucotrack.repositories.analysis_repository import AnalysisRepository
from glucotrack.repositories.session_repository import SessionRepository
from glucotrack.services.analysis_service import AnalysisService

ANALYSIS_RESULT = {
    "nutrition": {
        "carbs_g": 50,
        "proteins_g": 25,
        "fats_g": 12,
        "gi_estimate": 70,
        "gi_category": "high",
        "food_items": ["pasta"],
        "glucose_impact_narrative": "High-GI meal expected within 70–140 mg/dL range.",
        "notes": "",
    },
    "activity": {
        "description": "20-min walk",
        "glucose_modulation": "reduced post-meal spike",
        "effect_summary": "moderate lowering",
    },
    "glucose_curve": [
        {
            "timing_label": "before",
            "estimated_value_mg_dl": 90,
            "in_range": True,
            "notes": "",
            "curve_shape_label": "stable within range",
        },
        {
            "timing_label": "2h after",
            "estimated_value_mg_dl": 130,
            "in_range": True,
            "notes": "",
            "curve_shape_label": "gradual rise with plateau",
        },
    ],
    "correlation": {
        "spikes": [],
        "dips": [],
        "stable_zones": ["2h after"],
        "summary": "Good control with pasta meal",
    },
    "recommendations": [{"priority": 1, "text": "Maintain current eating pattern with pasta"}],
    "target_range_note": "All readings within 70–140 mg/dL.",
    "cgm_parseable": True,
    "cgm_parse_error": None,
}


class TestAnalysisFlow:
    """Full US2 integration: session → AI → AIAnalysis row → Telegram message."""

    @pytest.mark.asyncio
    async def test_full_analysis_flow(self, test_db, sample_user, sample_session):
        # Prepare session with entries
        sess_repo = SessionRepository(test_db)
        await sess_repo.add_food_entry(
            sample_user.telegram_user_id, sample_session.id, "food.jpg", "tg_f"
        )
        await sess_repo.add_cgm_entry(
            sample_user.telegram_user_id, sample_session.id, "cgm.jpg", "tg_c", "1h after"
        )
        await sess_repo.complete_session(sample_user.telegram_user_id, sample_session.id)

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=ANALYSIS_RESULT)
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
            chat_id=99999,
            bot=mock_bot,
        )

        # AIAnalysis persisted with correct user_id
        analysis_repo = AnalysisRepository(test_db)
        analysis = await analysis_repo.get_analysis_by_session(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
        )
        assert analysis is not None
        assert analysis.user_id == sample_user.telegram_user_id

        nutrition = json.loads(analysis.nutrition_json)
        assert nutrition["carbs_g"] == 50

        # Telegram send_message called
        assert mock_bot.send_message.called

    @pytest.mark.asyncio
    async def test_telegram_message_contains_four_sections(
        self, test_db, sample_user, sample_session
    ):
        """Analysis message contains all 4 sections (spec acceptance criterion)."""
        sess_repo = SessionRepository(test_db)
        await sess_repo.add_food_entry(sample_user.telegram_user_id, sample_session.id, "p", "t")
        await sess_repo.add_cgm_entry(
            sample_user.telegram_user_id, sample_session.id, "p2", "t2", "1h"
        )
        await sess_repo.complete_session(sample_user.telegram_user_id, sample_session.id)

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=ANALYSIS_RESULT)
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

        call_args = mock_bot.send_message.call_args
        text = call_args[1].get("text", "") or str(call_args)
        # All 4 sections must be present
        assert "Nutrition" in text
        assert "Glucose" in text
        assert "Correlation" in text
        assert "Recommendations" in text

    @pytest.mark.asyncio
    async def test_analysis_user_id_isolation(self, test_db):
        """Analysis is scoped to owning user — another user cannot retrieve it (Constitution II)."""
        from glucotrack.domain.user import get_or_create_user

        user_a = await get_or_create_user(test_db, telegram_user_id=201)
        user_b = await get_or_create_user(test_db, telegram_user_id=202)

        sess_repo = SessionRepository(test_db)
        session_a = await sess_repo.create_session(user_id=user_a.telegram_user_id)
        await sess_repo.add_food_entry(user_a.telegram_user_id, session_a.id, "p", "t")
        await sess_repo.add_cgm_entry(user_a.telegram_user_id, session_a.id, "p2", "t2", "1h")
        await sess_repo.complete_session(user_a.telegram_user_id, session_a.id)

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=ANALYSIS_RESULT)
        mock_bot = AsyncMock()
        mock_miro = AsyncMock()

        service = AnalysisService(
            db=test_db,
            ai_service=mock_ai,
            miro_service=mock_miro,
            storage_root="./data",
        )
        await service.run_analysis(
            user_id=user_a.telegram_user_id,
            session_id=session_a.id,
            chat_id=201,
            bot=mock_bot,
        )

        analysis_repo = AnalysisRepository(test_db)
        # User B should NOT be able to retrieve User A's analysis
        user_b_analysis = await analysis_repo.get_analysis_by_session(
            user_id=user_b.telegram_user_id,
            session_id=session_a.id,
        )
        assert user_b_analysis is None

    @pytest.mark.asyncio
    async def test_analysis_calls_enhanced_miro_card(self, test_db, sample_user, sample_session):
        """run_analysis() calls create_enhanced_session_card with correct args (T015, feature 002)."""
        sess_repo = SessionRepository(test_db)
        await sess_repo.add_food_entry(
            sample_user.telegram_user_id,
            sample_session.id,
            f"users/{sample_user.telegram_user_id}/sessions/{sample_session.id}/food_tg_f.jpg",
            "tg_f",
        )
        await sess_repo.add_cgm_entry(
            sample_user.telegram_user_id,
            sample_session.id,
            f"users/{sample_user.telegram_user_id}/sessions/{sample_session.id}/cgm_tg_c.jpg",
            "tg_c",
            "1h after",
        )
        await sess_repo.complete_session(sample_user.telegram_user_id, sample_session.id)

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=ANALYSIS_RESULT)
        mock_bot = AsyncMock()
        mock_miro = AsyncMock()
        mock_miro.create_enhanced_session_card = AsyncMock(return_value="frame-from-enhanced")

        service = AnalysisService(
            db=test_db,
            ai_service=mock_ai,
            miro_service=mock_miro,
            storage_root="./data",
        )
        await service.run_analysis(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            chat_id=99999,
            bot=mock_bot,
        )

        # create_enhanced_session_card must have been called (fire-and-forget, so give it a moment)
        import asyncio
        await asyncio.sleep(0)  # yield to allow background tasks to start

        # Check that the new method is wired — either called directly or via create_task
        # The mock_miro.create_enhanced_session_card should be called with analysis + session_images
        assert mock_miro.create_enhanced_session_card.called or mock_miro.create_session_card.called, (
            "Either create_enhanced_session_card or create_session_card must be called"
        )

        # Specifically check create_enhanced_session_card was called (not the old method)
        assert mock_miro.create_enhanced_session_card.called, (
            "create_enhanced_session_card must be called for feature 002"
        )
        call_kwargs = mock_miro.create_enhanced_session_card.call_args
        assert call_kwargs is not None
        # session_images arg should contain at least one entry with correct structure
        session_images = call_kwargs[1].get("session_images") or (
            call_kwargs[0][1] if len(call_kwargs[0]) > 1 else []
        )
        assert isinstance(session_images, list), "session_images must be a list"
        for img in session_images:
            assert "type" in img
            assert img["type"] in ("food", "cgm")
            assert "file_bytes" in img
            assert "telegram_file_id" in img
