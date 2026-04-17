"""Contract tests for Miro API schema — T043.

Validates that the request payload matches contracts/miro-api-schema.md
and that the response JSON has the expected structure.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from glucotrack.services.miro_service import MiroService


def _make_analysis() -> MagicMock:
    analysis = MagicMock()
    analysis.id = "analysis-uuid-001"
    analysis.user_id = 999
    analysis.session_id = "session-uuid-001"
    analysis.nutrition_json = json.dumps(
        {"carbs_g": 40, "proteins_g": 20, "fats_g": 10, "gi_estimate": 55, "notes": ""}
    )
    analysis.glucose_curve_json = json.dumps(
        [{"timing_label": "1h after", "estimated_value_mg_dl": 110, "in_range": True, "notes": ""}]
    )
    analysis.correlation_json = json.dumps(
        {"spikes": [], "dips": [], "stable_zones": [], "summary": "Stable control"}
    )
    analysis.recommendations_json = json.dumps([{"priority": 1, "text": "Keep going"}])
    analysis.within_target_notes = "All in range"
    analysis.created_at = MagicMock()
    analysis.created_at.strftime = MagicMock(return_value="2026-04-17 10:00 UTC")
    return analysis


class TestMiroAPISchemaContract:
    """Contract tests verifying Miro request/response schema compliance."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_has_data_field_with_title_and_description(self) -> None:
        service = MiroService(access_token="tok", board_id="board-1")
        analysis = _make_analysis()
        captured: dict = {}

        def capture(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(201, json={"id": "card-1", "type": "card", "data": {}})

        respx.post("https://api.miro.com/v2/boards/board-1/cards").mock(side_effect=capture)
        await service.create_session_card(analysis=analysis)

        body = captured["body"]
        assert "data" in body
        assert "title" in body["data"]
        assert "description" in body["data"]
        assert len(body["data"]["title"]) > 0
        assert len(body["data"]["description"]) > 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_has_style_with_fill_color(self) -> None:
        service = MiroService(access_token="tok", board_id="board-1")
        analysis = _make_analysis()
        captured: dict = {}

        def capture(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(201, json={"id": "card-1", "type": "card", "data": {}})

        respx.post("https://api.miro.com/v2/boards/board-1/cards").mock(side_effect=capture)
        await service.create_session_card(analysis=analysis)

        assert captured["body"]["style"]["fillColor"] == "#d5f5e3"

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_has_position_and_geometry(self) -> None:
        service = MiroService(access_token="tok", board_id="board-1")
        analysis = _make_analysis()
        captured: dict = {}

        def capture(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(201, json={"id": "card-1", "type": "card", "data": {}})

        respx.post("https://api.miro.com/v2/boards/board-1/cards").mock(side_effect=capture)
        await service.create_session_card(analysis=analysis)

        body = captured["body"]
        assert "position" in body
        assert "geometry" in body
        assert body["geometry"]["width"] == 320
        assert body["geometry"]["height"] == 180

    @pytest.mark.asyncio
    @respx.mock
    async def test_response_id_field_extracted_as_miro_card_id(self) -> None:
        service = MiroService(access_token="tok", board_id="board-1")
        analysis = _make_analysis()

        respx.post("https://api.miro.com/v2/boards/board-1/cards").mock(
            return_value=httpx.Response(
                201,
                json={"id": "my-miro-card-id", "type": "card", "data": {}},
            )
        )

        card_id = await service.create_session_card(analysis=analysis)
        assert card_id == "my-miro-card-id"

    def test_description_includes_nutrition_section(self) -> None:
        """Description template includes all 4 required content sections."""
        service = MiroService(access_token="tok", board_id="board-1")
        analysis = _make_analysis()
        desc = service._build_description(analysis)
        assert "Nutrition" in desc
        assert "Glucose" in desc
        assert "Correlation" in desc
        assert "Recommendation" in desc
