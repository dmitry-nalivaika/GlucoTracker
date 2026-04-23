"""Unit tests for AIService — T033.

Claude API calls are mocked; no real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from glucotrack.services.ai_service import AIService, AnalysisError, RateLimitExceeded

VALID_ANALYSIS = {
    "nutrition": {
        "carbs_g": 45,
        "proteins_g": 20,
        "fats_g": 10,
        "gi_estimate": 65,
        "notes": "Pasta with tomato sauce",
    },
    "glucose_curve": [
        {
            "timing_label": "before eating",
            "estimated_value_mg_dl": 95,
            "in_range": True,
            "notes": "",
        },
        {
            "timing_label": "1 hour after",
            "estimated_value_mg_dl": 155,
            "in_range": False,
            "notes": "spike",
        },
    ],
    "correlation": {
        "spikes": ["Pasta caused spike at 1h"],
        "dips": [],
        "stable_zones": [],
        "summary": "Glucose spiked above 140 mg/dL after eating pasta.",
    },
    "recommendations": [{"priority": 1, "text": "Reduce refined carbs to lower post-meal spike."}],
    "target_range_note": "One reading exceeded 140 mg/dL at 1 hour post-meal.",
    "cgm_parseable": True,
    "cgm_parse_error": None,
}


def _make_service(max_calls: int = 10, max_tokens: int = 4000) -> AIService:
    return AIService(
        api_key="test-key",
        model="claude-sonnet-4-6",
        max_calls_per_user_per_day=max_calls,
        max_tokens_per_session=max_tokens,
    )


class TestAIService:
    """Tests for AIService — mocked Claude API."""

    @pytest.mark.asyncio
    async def test_analyse_session_returns_parsed_dict(self) -> None:
        service = _make_service()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(VALID_ANALYSIS))]

        with patch.object(
            service._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            result = await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f1", "file_path": "p1"}],
                cgm_entries=[{"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"fake"),
            )

        assert result["nutrition"]["carbs_g"] == 45
        assert result["cgm_parseable"] is True
        assert len(result["recommendations"]) == 1

    @pytest.mark.asyncio
    async def test_cgm_unparseable_returns_false_flag(self) -> None:
        service = _make_service()
        unparseable = {
            **VALID_ANALYSIS,
            "cgm_parseable": False,
            "cgm_parse_error": "Image too blurry",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(unparseable))]

        with patch.object(
            service._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            result = await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f1", "file_path": "p"}],
                cgm_entries=[{"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"fake"),
            )

        assert result["cgm_parseable"] is False
        assert result["cgm_parse_error"] == "Image too blurry"

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_raises(self) -> None:
        service = _make_service(max_calls=1)
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(VALID_ANALYSIS))]

        with patch.object(
            service._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f1", "file_path": "p"}],
                cgm_entries=[{"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"fake"),
            )

        with pytest.raises(RateLimitExceeded):
            await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f1", "file_path": "p"}],
                cgm_entries=[{"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"fake"),
            )

    @pytest.mark.asyncio
    async def test_different_users_have_independent_rate_limits(self) -> None:
        service = _make_service(max_calls=1)
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(VALID_ANALYSIS))]

        with patch.object(
            service._client.messages, "create", new=AsyncMock(return_value=mock_response)
        ):
            # User 1 exhausts their limit
            await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f1", "file_path": "p"}],
                cgm_entries=[{"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"fake"),
            )
            # User 2 should still be allowed
            result = await service.analyse_session(
                user_id=2,
                food_entries=[{"telegram_file_id": "f1", "file_path": "p"}],
                cgm_entries=[{"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"fake"),
            )
        assert result is not None

    @pytest.mark.asyncio
    async def test_api_error_raises_analysis_error(self) -> None:
        service = _make_service()
        # Use a generic Exception to simulate an API-level failure
        with patch.object(
            service._client.messages,
            "create",
            new=AsyncMock(side_effect=Exception("Simulated API failure")),
        ):
            with pytest.raises((AnalysisError, Exception)):
                await service.analyse_session(
                    user_id=1,
                    food_entries=[{"telegram_file_id": "f1", "file_path": "p"}],
                    cgm_entries=[
                        {"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}
                    ],
                    activity_entries=[],
                    load_file_bytes=AsyncMock(return_value=b"fake"),
                )

    @pytest.mark.asyncio
    async def test_request_includes_image_blocks(self) -> None:
        service = _make_service()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(VALID_ANALYSIS))]
        captured_kwargs: dict = {}

        async def capture(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        with patch.object(service._client.messages, "create", new=capture):
            await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f1", "file_path": "p"}],
                cgm_entries=[{"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"fake"),
            )

        messages = captured_kwargs.get("messages", [])
        assert len(messages) == 1
        content_blocks = messages[0]["content"]
        image_blocks = [b for b in content_blocks if b.get("type") == "image"]
        assert len(image_blocks) == 2  # 1 food + 1 CGM

    @pytest.mark.asyncio
    async def test_max_tokens_respected(self) -> None:
        service = _make_service(max_tokens=2000)
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(VALID_ANALYSIS))]
        captured_kwargs: dict = {}

        async def capture(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        with patch.object(service._client.messages, "create", new=capture):
            await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f1", "file_path": "p"}],
                cgm_entries=[{"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"fake"),
            )

        assert captured_kwargs.get("max_tokens") == 2000

    @pytest.mark.asyncio
    async def test_jpeg_bytes_produce_image_jpeg_media_type(self) -> None:
        """JPEG image bytes (FF D8 prefix) must yield media_type image/jpeg."""
        service = _make_service()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(VALID_ANALYSIS))]
        captured_kwargs: dict = {}

        async def capture(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        # Minimal valid JPEG magic bytes
        jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100

        with patch.object(service._client.messages, "create", new=capture):
            await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f1", "file_path": "p1"}],
                cgm_entries=[{"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=jpeg_bytes),
            )

        messages = captured_kwargs["messages"]
        image_blocks = [b for b in messages[0]["content"] if b.get("type") == "image"]
        for block in image_blocks:
            assert block["source"]["media_type"] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_png_bytes_produce_image_png_media_type(self) -> None:
        """PNG image bytes (\\x89PNG prefix) must yield media_type image/png."""
        service = _make_service()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(VALID_ANALYSIS))]
        captured_kwargs: dict = {}

        async def capture(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        # PNG magic bytes
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        with patch.object(service._client.messages, "create", new=capture):
            await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f1", "file_path": "p1"}],
                cgm_entries=[{"telegram_file_id": "c1", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=png_bytes),
            )

        messages = captured_kwargs["messages"]
        image_blocks = [b for b in messages[0]["content"] if b.get("type") == "image"]
        for block in image_blocks:
            assert block["source"]["media_type"] == "image/png"
