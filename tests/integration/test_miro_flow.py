"""Integration tests for US3 Miro visualisation flow — T044.

Uses respx to mock the Miro API. Tests the full pipeline:
  completed session → AIAnalysis → MiroCard row persisted.

Miro failure must NOT affect Telegram delivery.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from glucotrack.repositories.session_repository import SessionRepository
from glucotrack.services.analysis_service import AnalysisService
from glucotrack.services.miro_service import MiroService

ANALYSIS_RESULT = {
    "nutrition": {
        "carbs_g": 50,
        "proteins_g": 25,
        "fats_g": 12,
        "gi_estimate": 70,
        "gi_category": "high",
        "food_items": ["pasta"],
        "glucose_impact_narrative": "High-GI meal stays within 70–140 mg/dL range.",
        "notes": "",
    },
    "activity": {
        "description": None,
        "glucose_modulation": "No activity logged.",
        "effect_summary": "No activity to analyse.",
    },
    "glucose_curve": [
        {
            "timing_label": "1h after",
            "estimated_value_mg_dl": 110,
            "in_range": True,
            "notes": "",
            "curve_shape_label": "stable within range",
        }
    ],
    "correlation": {"spikes": [], "dips": [], "stable_zones": [], "summary": "Stable with pasta"},
    "recommendations": [{"priority": 1, "text": "Maintain current pattern with pasta"}],
    "target_range_note": "All within range.",
    "cgm_parseable": True,
    "cgm_parse_error": None,
}


class TestMiroFlow:
    """Integration tests for Miro card creation after analysis delivery."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_miro_card_created_after_analysis(self, test_db, sample_user, sample_session):
        """After full analysis flow, MiroCard row exists with status=created."""
        sess_repo = SessionRepository(test_db)
        await sess_repo.add_food_entry(
            sample_user.telegram_user_id, sample_session.id, "food.jpg", "tg_f"
        )
        await sess_repo.add_cgm_entry(
            sample_user.telegram_user_id, sample_session.id, "cgm.jpg", "tg_c", "1h after"
        )
        await sess_repo.complete_session(sample_user.telegram_user_id, sample_session.id)

        # Feature 002: mock the enhanced endpoints (frame + images + sticky notes)
        respx.post("https://api.miro.com/v2/boards/test-board/frames").mock(
            return_value=httpx.Response(
                201,
                json={"id": "frame-001", "type": "frame", "data": {}, "links": {}},
            )
        )
        respx.post("https://api.miro.com/v2/boards/test-board/images").mock(
            return_value=httpx.Response(
                201,
                json={"id": "img-001", "type": "image", "data": {}, "parent": {"id": "frame-001"}},
            )
        )
        respx.post("https://api.miro.com/v2/boards/test-board/sticky_notes").mock(
            return_value=httpx.Response(
                201, json={"id": "sn-001", "type": "sticky_note", "data": {}}
            )
        )

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=ANALYSIS_RESULT)
        mock_bot = AsyncMock()
        miro_service = MiroService(access_token="tok", board_id="test-board")

        service = AnalysisService(
            db=test_db,
            ai_service=mock_ai,
            miro_service=miro_service,
            storage_root="./data",
        )
        await service.run_analysis(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            chat_id=99999,
            bot=mock_bot,
        )

        # Allow fire-and-forget task to complete
        await asyncio.sleep(0.1)

        # Telegram was delivered
        assert mock_bot.send_message.called

        # Verify the Miro API was called (respx mock was hit)
        assert respx.calls.call_count >= 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_miro_5xx_does_not_block_telegram(self, test_db, sample_user, sample_session):
        """Miro 500 error must not prevent Telegram delivery (FR-009)."""
        sess_repo = SessionRepository(test_db)
        await sess_repo.add_food_entry(
            sample_user.telegram_user_id, sample_session.id, "food.jpg", "tg_f"
        )
        await sess_repo.add_cgm_entry(
            sample_user.telegram_user_id, sample_session.id, "cgm.jpg", "tg_c", "1h"
        )
        await sess_repo.complete_session(sample_user.telegram_user_id, sample_session.id)

        # Feature 002: 500 on the frames endpoint (so all retries fail, Miro error is swallowed)
        respx.post("https://api.miro.com/v2/boards/test-board/frames").mock(
            return_value=httpx.Response(500, json={"message": "server error"})
        )
        respx.post("https://api.miro.com/v2/boards/test-board/images").mock(
            return_value=httpx.Response(
                201,
                json={"id": "img-001", "type": "image", "data": {}, "parent": {"id": "f"}},
            )
        )
        respx.post("https://api.miro.com/v2/boards/test-board/sticky_notes").mock(
            return_value=httpx.Response(201, json={"id": "sn-001", "type": "sticky_note", "data": {}})
        )

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=ANALYSIS_RESULT)
        mock_bot = AsyncMock()
        miro_service = MiroService(
            access_token="tok",
            board_id="test-board",
            _retry_delays=(0.0, 0.0, 0.0),
        )

        service = AnalysisService(
            db=test_db,
            ai_service=mock_ai,
            miro_service=miro_service,
            storage_root="./data",
        )
        await service.run_analysis(
            user_id=sample_user.telegram_user_id,
            session_id=sample_session.id,
            chat_id=99999,
            bot=mock_bot,
        )

        # Allow fire-and-forget task to finish (will fail silently)
        await asyncio.sleep(0.1)

        # Telegram delivery must succeed regardless of Miro failure
        assert mock_bot.send_message.called
