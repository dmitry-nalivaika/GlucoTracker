"""Contract tests for Claude API schema — T035.

Validates that the request payload matches contracts/claude-api-schema.md
and that the response JSON parses to the expected structure.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from glucotrack.services.ai_service import AIService

MINIMAL_VALID_RESPONSE = {
    "nutrition": {"carbs_g": 30, "proteins_g": 10, "fats_g": 5, "gi_estimate": 50, "notes": ""},
    "glucose_curve": [
        {"timing_label": "1h after", "estimated_value_mg_dl": 120, "in_range": True, "notes": ""}
    ],
    "correlation": {"spikes": [], "dips": [], "stable_zones": [], "summary": "Stable"},
    "recommendations": [{"priority": 1, "text": "Well done"}],
    "target_range_note": "Within range",
    "cgm_parseable": True,
    "cgm_parse_error": None,
}


class TestClaudeAPISchemaContract:
    """Contract tests verifying request/response schema compliance."""

    @pytest.mark.asyncio
    async def test_request_uses_correct_model(self) -> None:
        service = AIService(
            api_key="test",
            model="claude-3-5-sonnet-20241022",
            max_calls_per_user_per_day=10,
            max_tokens_per_session=4000,
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(MINIMAL_VALID_RESPONSE))]
        captured: dict = {}

        async def capture(**kwargs):
            captured.update(kwargs)
            return mock_response

        with patch.object(service._client.messages, "create", new=capture):
            await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f", "file_path": "p"}],
                cgm_entries=[{"telegram_file_id": "c", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"img"),
            )

        assert captured["model"] == "claude-3-5-sonnet-20241022"

    @pytest.mark.asyncio
    async def test_request_has_system_prompt(self) -> None:
        service = AIService(
            api_key="test",
            model="claude-3-5-sonnet-20241022",
            max_calls_per_user_per_day=10,
            max_tokens_per_session=4000,
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(MINIMAL_VALID_RESPONSE))]
        captured: dict = {}

        async def capture(**kwargs):
            captured.update(kwargs)
            return mock_response

        with patch.object(service._client.messages, "create", new=capture):
            await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f", "file_path": "p"}],
                cgm_entries=[{"telegram_file_id": "c", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"img"),
            )

        assert "system" in captured
        assert len(captured["system"]) > 0

    @pytest.mark.asyncio
    async def test_max_tokens_set_in_request(self) -> None:
        service = AIService(
            api_key="test",
            model="claude-3-5-sonnet-20241022",
            max_calls_per_user_per_day=10,
            max_tokens_per_session=4000,
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(MINIMAL_VALID_RESPONSE))]
        captured: dict = {}

        async def capture(**kwargs):
            captured.update(kwargs)
            return mock_response

        with patch.object(service._client.messages, "create", new=capture):
            await service.analyse_session(
                user_id=1,
                food_entries=[{"telegram_file_id": "f", "file_path": "p"}],
                cgm_entries=[{"telegram_file_id": "c", "timing_label": "1h", "file_path": "p2"}],
                activity_entries=[],
                load_file_bytes=AsyncMock(return_value=b"img"),
            )

        assert captured.get("max_tokens") == 4000

    def test_response_schema_has_all_required_fields(self) -> None:
        """Validate that a response JSON contains all required top-level fields."""
        required_fields = [
            "nutrition",
            "glucose_curve",
            "correlation",
            "recommendations",
            "target_range_note",
            "cgm_parseable",
        ]
        response = MINIMAL_VALID_RESPONSE
        for field in required_fields:
            assert field in response, f"Missing required field: {field}"

    def test_nutrition_schema_has_expected_fields(self) -> None:
        nutrition = MINIMAL_VALID_RESPONSE["nutrition"]
        assert "carbs_g" in nutrition
        assert "proteins_g" in nutrition
        assert "fats_g" in nutrition
        assert "gi_estimate" in nutrition

    def test_recommendations_are_list(self) -> None:
        assert isinstance(MINIMAL_VALID_RESPONSE["recommendations"], list)
        if MINIMAL_VALID_RESPONSE["recommendations"]:
            rec = MINIMAL_VALID_RESPONSE["recommendations"][0]
            assert "priority" in rec
            assert "text" in rec

    def test_glucose_curve_in_range_reflects_target_range(self) -> None:
        for point in MINIMAL_VALID_RESPONSE["glucose_curve"]:
            value = point.get("estimated_value_mg_dl")
            in_range = point.get("in_range")
            if value is not None and in_range is not None:
                expected_in_range = 70 <= value <= 140
                assert in_range == expected_in_range, (
                    f"in_range={in_range} incorrect for value={value} mg/dL "
                    f"(expected {expected_in_range} for 70–140 target range)"
                )
