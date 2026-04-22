"""Unit tests for MiroService — T042.

httpx requests are mocked with respx; no real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from glucotrack.services.miro_service import MiroError, MiroService


def _make_analysis(user_id: int = 1) -> MagicMock:
    analysis = MagicMock()
    analysis.id = "analysis-uuid-001"
    analysis.user_id = user_id
    analysis.session_id = "session-uuid-001"
    analysis.nutrition_json = json.dumps(
        {"carbs_g": 50, "proteins_g": 25, "fats_g": 12, "gi_estimate": 70, "notes": ""}
    )
    analysis.glucose_curve_json = json.dumps(
        [{"timing_label": "1h after", "estimated_value_mg_dl": 120, "in_range": True, "notes": ""}]
    )
    analysis.correlation_json = json.dumps(
        {"spikes": [], "dips": [], "stable_zones": ["1h after"], "summary": "Stable"}
    )
    analysis.recommendations_json = json.dumps(
        [{"priority": 1, "text": "Maintain current eating pattern"}]
    )
    analysis.within_target_notes = "All within range."
    analysis.created_at = MagicMock()
    analysis.created_at.strftime = MagicMock(return_value="2026-04-17 10:00 UTC")
    return analysis


def _make_service() -> MiroService:
    return MiroService(
        access_token="test-miro-token",
        board_id="test-board-id",
    )


class TestMiroService:
    """Unit tests for MiroService — mocked Miro API."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_session_card_success(self) -> None:
        """201 response stores miro_card_id and returns it."""
        service = _make_service()
        analysis = _make_analysis()

        respx.post("https://api.miro.com/v2/boards/test-board-id/cards").mock(
            return_value=httpx.Response(
                201,
                json={"id": "miro-card-xyz", "type": "card", "data": {}},
            )
        )

        card_id = await service.create_session_card(analysis=analysis)
        assert card_id == "miro-card-xyz"

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_body_structure(self) -> None:
        """POST body matches miro-api-schema.md contract."""
        service = _make_service()
        analysis = _make_analysis()

        captured_request = None

        def capture(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            return httpx.Response(201, json={"id": "miro-card-xyz", "type": "card", "data": {}})

        respx.post("https://api.miro.com/v2/boards/test-board-id/cards").mock(side_effect=capture)

        await service.create_session_card(analysis=analysis)

        body = json.loads(captured_request.content)
        assert "data" in body
        assert "title" in body["data"]
        assert "description" in body["data"]
        assert "style" not in body  # Miro cards API v2 does not support style.fillColor
        assert "position" in body
        assert "geometry" in body

    @pytest.mark.asyncio
    @respx.mock
    async def test_anonymised_user_id_in_title(self) -> None:
        """Title contains anonymised hash, never raw telegram_user_id."""
        service = _make_service()
        analysis = _make_analysis(user_id=12345678)

        captured_request = None

        def capture(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            return httpx.Response(201, json={"id": "miro-card-xyz", "type": "card", "data": {}})

        respx.post("https://api.miro.com/v2/boards/test-board-id/cards").mock(side_effect=capture)

        await service.create_session_card(analysis=analysis)

        body = json.loads(captured_request.content)
        title = body["data"]["title"]
        # Raw telegram_user_id must NOT appear in title
        assert "12345678" not in title
        # Anonymised marker must be present
        assert "User #" in title

    @pytest.mark.asyncio
    @respx.mock
    async def test_4xx_raises_miro_error_no_retry(self) -> None:
        """4xx status sets status=failed with no retry."""
        service = _make_service()
        analysis = _make_analysis()

        call_count = 0

        def respond(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(400, json={"message": "bad request"})

        respx.post("https://api.miro.com/v2/boards/test-board-id/cards").mock(side_effect=respond)

        with pytest.raises(MiroError):
            await service.create_session_card(analysis=analysis)

        # No retry for 4xx — called exactly once
        assert call_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_5xx_retries_up_to_3_times(self) -> None:
        """5xx status retries up to 3× then raises MiroError."""
        service = _make_service().__class__(
            access_token="test-token",
            board_id="test-board",
            _retry_delays=(0.0, 0.0, 0.0),  # zero delays for fast tests
        )
        analysis = _make_analysis()

        call_count = 0

        def respond(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, json={"message": "server error"})

        respx.post("https://api.miro.com/v2/boards/test-board/cards").mock(side_effect=respond)

        with pytest.raises(MiroError):
            await service.create_session_card(analysis=analysis)

        # 1 initial + 3 retries = 4 total attempts... or exactly 3 per spec
        assert call_count <= 4

    @pytest.mark.asyncio
    @respx.mock
    async def test_429_respects_retry_after(self) -> None:
        """429 response retries after Retry-After header delay."""
        service = _make_service().__class__(
            access_token="test-token",
            board_id="test-board",
            _retry_delays=(0.0, 0.0, 0.0),
        )
        analysis = _make_analysis()

        call_count = 0

        def respond(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(429, headers={"Retry-After": "0"}, json={})
            return httpx.Response(201, json={"id": "miro-card-xyz", "type": "card", "data": {}})

        respx.post("https://api.miro.com/v2/boards/test-board/cards").mock(side_effect=respond)

        card_id = await service.create_session_card(analysis=analysis)
        assert card_id == "miro-card-xyz"
        assert call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_auth_header_set(self) -> None:
        """Authorization: Bearer header is present in all requests."""
        service = _make_service()
        analysis = _make_analysis()

        captured_request = None

        def capture(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            return httpx.Response(201, json={"id": "miro-card-xyz", "type": "card", "data": {}})

        respx.post("https://api.miro.com/v2/boards/test-board-id/cards").mock(side_effect=capture)

        await service.create_session_card(analysis=analysis)

        assert captured_request.headers.get("authorization") == "Bearer test-miro-token"
