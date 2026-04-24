"""Integration tests for Russian language feature — T013, T017.

T013: Language preference persists in DB and is used across sessions.
T017: AnalysisService passes user's language to AIService.analyse_session.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from glucotrack.domain.user import get_or_create_user
from glucotrack.repositories.session_repository import SessionRepository
from glucotrack.repositories.user_repository import UserRepository, effective_lang
from glucotrack.services.analysis_service import AnalysisService

_ANALYSIS_RESULT = {
    "nutrition": {
        "carbs_g": 40,
        "proteins_g": 20,
        "fats_g": 10,
        "gi_estimate": 55,
        "gi_category": "medium",
        "food_items": ["rice"],
        "glucose_impact_narrative": "Medium-GI meal within 70–140 mg/dL range.",
        "notes": "",
    },
    "activity": None,
    "glucose_curve": [
        {
            "timing_label": "before",
            "estimated_value_mg_dl": 95,
            "in_range": True,
            "notes": "",
            "curve_shape_label": "stable within range",
        }
    ],
    "correlation": {
        "spikes": [],
        "dips": [],
        "stable_zones": [],
        "summary": "Stable overall.",
    },
    "recommendations": [],
    "target_range_note": None,
    "cgm_parseable": True,
    "cgm_parse_error": None,
}


class TestLanguagePersistence:
    """T013: Language preference survives across DB reads."""

    @pytest.mark.asyncio
    async def test_language_stored_and_retrieved(self, test_db) -> None:
        """Setting ru via UserRepository persists and effective_lang returns 'ru'."""
        await get_or_create_user(test_db, telegram_user_id=8001)
        await test_db.commit()

        repo = UserRepository(test_db)
        await repo.update_language(8001, "ru")
        await test_db.commit()

        user_refreshed = await repo.get_by_telegram_id(8001)
        assert effective_lang(user_refreshed) == "ru"

    @pytest.mark.asyncio
    async def test_language_defaults_to_en_when_unset(self, test_db) -> None:
        """New user without language_code gets 'en' from effective_lang."""
        user = await get_or_create_user(test_db, telegram_user_id=8002)
        await test_db.commit()

        assert effective_lang(user) == "en"

    @pytest.mark.asyncio
    async def test_language_can_be_changed(self, test_db) -> None:
        """Language preference can be updated from en to ru and back."""
        await get_or_create_user(test_db, telegram_user_id=8003)
        await test_db.commit()

        repo = UserRepository(test_db)
        await repo.update_language(8003, "ru")
        await test_db.commit()

        user = await repo.get_by_telegram_id(8003)
        assert effective_lang(user) == "ru"

        await repo.update_language(8003, "en")
        await test_db.commit()

        user = await repo.get_by_telegram_id(8003)
        assert effective_lang(user) == "en"


class TestAnalysisServiceLanguageThreading:
    """T017: AnalysisService passes user's language to AIService.analyse_session."""

    @pytest.mark.asyncio
    async def test_russian_user_calls_ai_with_language_ru(self, test_db) -> None:
        """When user has language_code='ru', analyse_session is called with language='ru'."""
        from glucotrack.domain.user import get_or_create_user

        await get_or_create_user(test_db, telegram_user_id=8010)
        await test_db.commit()

        repo = UserRepository(test_db)
        await repo.update_language(8010, "ru")
        await test_db.commit()

        sess_repo = SessionRepository(test_db)
        session = await sess_repo.create_session(user_id=8010)
        await sess_repo.add_food_entry(8010, session.id, "food.jpg", "tg_f1")
        await sess_repo.add_cgm_entry(8010, session.id, "cgm.jpg", "tg_c1", "1h after")
        await sess_repo.complete_session(8010, session.id)

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=_ANALYSIS_RESULT)
        mock_bot = AsyncMock()
        mock_miro = None

        service = AnalysisService(
            db=test_db,
            ai_service=mock_ai,
            miro_service=mock_miro,
            storage_root="./data",
        )
        await service.run_analysis(
            user_id=8010,
            session_id=session.id,
            chat_id=8010,
            bot=mock_bot,
        )
        await asyncio.sleep(0.05)

        assert mock_ai.analyse_session.called
        call_kwargs = mock_ai.analyse_session.call_args[1]
        assert (
            call_kwargs.get("language") == "ru"
        ), f"Expected language='ru' but got: {call_kwargs.get('language')!r}"

    @pytest.mark.asyncio
    async def test_english_user_calls_ai_with_language_en(self, test_db) -> None:
        """When user has no language_code, analyse_session is called with language='en'."""
        await get_or_create_user(test_db, telegram_user_id=8011)
        await test_db.commit()

        sess_repo = SessionRepository(test_db)
        session = await sess_repo.create_session(user_id=8011)
        await sess_repo.add_food_entry(8011, session.id, "food.jpg", "tg_f2")
        await sess_repo.add_cgm_entry(8011, session.id, "cgm.jpg", "tg_c2", "1h after")
        await sess_repo.complete_session(8011, session.id)

        mock_ai = AsyncMock()
        mock_ai.analyse_session = AsyncMock(return_value=_ANALYSIS_RESULT)
        mock_bot = AsyncMock()

        service = AnalysisService(
            db=test_db,
            ai_service=mock_ai,
            miro_service=None,
            storage_root="./data",
        )
        await service.run_analysis(
            user_id=8011,
            session_id=session.id,
            chat_id=8011,
            bot=mock_bot,
        )

        assert mock_ai.analyse_session.called
        call_kwargs = mock_ai.analyse_session.call_args[1]
        assert call_kwargs.get("language") == "en"
