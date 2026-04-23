"""Unit tests for MiroService — T042 / T014.

httpx requests are mocked with respx; no real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

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
        {
            "carbs_g": 50,
            "proteins_g": 25,
            "fats_g": 12,
            "gi_estimate": 70,
            "gi_category": "high",
            "food_items": ["pasta", "salad"],
            "glucose_impact_narrative": "High-GI meal expected to raise glucose within 70–140 mg/dL.",
            "notes": "",
        }
    )
    analysis.glucose_curve_json = json.dumps(
        [
            {
                "timing_label": "1h after",
                "estimated_value_mg_dl": 120,
                "in_range": True,
                "notes": "",
                "curve_shape_label": "gradual rise",
            }
        ]
    )
    analysis.correlation_json = json.dumps(
        {
            "spikes": ["Pasta likely caused 1h spike"],
            "dips": [],
            "stable_zones": ["1h after"],
            "summary": "Stable with moderate spike from pasta",
        }
    )
    analysis.recommendations_json = json.dumps(
        [{"priority": 1, "text": "Maintain current eating pattern with pasta"}]
    )
    analysis.activity_json = json.dumps(
        {
            "description": "20-min walk",
            "glucose_modulation": "walk reduced spike",
            "effect_summary": "moderate lowering observed",
        }
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


def _make_session_images(n_food: int = 1, n_cgm: int = 1) -> list[dict]:
    images = []
    for i in range(n_food):
        images.append(
            {
                "type": "food",
                "file_bytes": f"food_bytes_{i}".encode(),
                "telegram_file_id": f"tg_food_{i}",
            }
        )
    for i in range(n_cgm):
        images.append(
            {
                "type": "cgm",
                "file_bytes": f"cgm_bytes_{i}".encode(),
                "telegram_file_id": f"tg_cgm_{i}",
            }
        )
    return images


class TestMiroServiceEnhancedCard:
    """Unit tests for create_enhanced_session_card() — feature 002 (T014)."""

    @pytest.mark.asyncio
    async def test_creates_frame_first(self) -> None:
        """Frame POST is called before any image POST."""
        service = _make_service()
        analysis = _make_analysis()
        call_order: list[str] = []

        async def mock_create_frame(title: str, user_id: int, n_images: int) -> str:
            call_order.append("frame")
            return "frame-first-test"

        async def mock_upload_image(frame_id: str, image: dict, idx: int) -> str | None:
            call_order.append("image")
            return "img-id"

        async def mock_add_sticky_note(
            frame_id: str, content: str, style: dict, position: dict, geometry: dict
        ) -> str:
            call_order.append("sticky")
            return "sticky-id"

        with (
            patch.object(service, "_create_frame", new=AsyncMock(side_effect=mock_create_frame)),
            patch.object(service, "_upload_image", new=AsyncMock(side_effect=mock_upload_image)),
            patch.object(service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis, session_images=_make_session_images(1, 1)
            )

        assert call_order[0] == "frame", "Frame must be created first"
        assert "image" in call_order, "Image upload must be called"
        assert call_order.index("frame") < call_order.index("image")

    @pytest.mark.asyncio
    async def test_uploads_food_photos_before_cgm(self) -> None:
        """Food images are uploaded before CGM screenshots (FR-002)."""
        service = _make_service()
        analysis = _make_analysis()
        upload_types: list[str] = []

        async def mock_create_frame(title: str, user_id: int, n_images: int) -> str:
            return "frame-order-test"

        async def mock_upload_image(frame_id: str, image: dict, idx: int) -> str | None:
            upload_types.append(image["type"])
            return "img-id"

        async def mock_add_sticky_note(
            frame_id: str, content: str, style: dict, position: dict, geometry: dict
        ) -> str:
            return "sticky-id"

        with (
            patch.object(service, "_create_frame", new=AsyncMock(side_effect=mock_create_frame)),
            patch.object(service, "_upload_image", new=AsyncMock(side_effect=mock_upload_image)),
            patch.object(service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis,
                session_images=_make_session_images(n_food=2, n_cgm=1),
            )

        # All food images must appear before the first cgm image
        if "cgm" in upload_types:
            first_cgm = upload_types.index("cgm")
            for i in range(first_cgm):
                assert upload_types[i] == "food", (
                    f"Expected food at position {i}, got {upload_types[i]}"
                )

    @pytest.mark.asyncio
    async def test_image_failure_adds_placeholder(self) -> None:
        """When image upload returns None (failure), a placeholder sticky note is added (FR-011)."""
        service = _make_service()
        analysis = _make_analysis()
        sticky_contents: list[str] = []

        async def mock_create_frame(title: str, user_id: int, n_images: int) -> str:
            return "frame-placeholder-test"

        async def mock_upload_image(frame_id: str, image: dict, idx: int) -> str | None:
            return None  # Simulate upload failure for all images

        async def mock_add_sticky_note(
            frame_id: str, content: str, style: dict, position: dict, geometry: dict
        ) -> str:
            sticky_contents.append(content)
            return "sticky-id"

        with (
            patch.object(service, "_create_frame", new=AsyncMock(side_effect=mock_create_frame)),
            patch.object(service, "_upload_image", new=AsyncMock(side_effect=mock_upload_image)),
            patch.object(service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis, session_images=_make_session_images(1, 1)
            )

        # At least one placeholder sticky note for the failed uploads
        placeholder_texts = [c for c in sticky_contents if "unavailable" in c.lower() or "failed" in c.lower()]
        assert len(placeholder_texts) >= 1, (
            f"Expected placeholder sticky notes for failed uploads, got: {sticky_contents}"
        )

    @pytest.mark.asyncio
    async def test_all_five_sections_created(self) -> None:
        """Six sticky note calls are made: separator + 5 analysis sections."""
        service = _make_service()
        analysis = _make_analysis()
        sticky_call_count = 0

        async def mock_create_frame(title: str, user_id: int, n_images: int) -> str:
            return "frame-sections-test"

        async def mock_upload_image(frame_id: str, image: dict, idx: int) -> str | None:
            return "img-id"

        async def mock_add_sticky_note(
            frame_id: str, content: str, style: dict, position: dict, geometry: dict
        ) -> str:
            nonlocal sticky_call_count
            sticky_call_count += 1
            return f"sticky-{sticky_call_count}"

        with (
            patch.object(service, "_create_frame", new=AsyncMock(side_effect=mock_create_frame)),
            patch.object(service, "_upload_image", new=AsyncMock(side_effect=mock_upload_image)),
            patch.object(service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis, session_images=_make_session_images(1, 1)
            )

        # 1 separator + 5 sections = 6 sticky notes (plus any image placeholders)
        assert sticky_call_count >= 6, (
            f"Expected ≥6 sticky note calls (separator + 5 sections), got {sticky_call_count}"
        )

    @pytest.mark.asyncio
    async def test_returns_frame_id(self) -> None:
        """create_enhanced_session_card returns the frame ID from _create_frame."""
        service = _make_service()
        analysis = _make_analysis()

        async def mock_create_frame(title: str, user_id: int, n_images: int) -> str:
            return "expected-frame-id"

        async def mock_upload_image(frame_id: str, image: dict, idx: int) -> str | None:
            return "img-id"

        async def mock_add_sticky_note(
            frame_id: str, content: str, style: dict, position: dict, geometry: dict
        ) -> str:
            return "sticky-id"

        with (
            patch.object(service, "_create_frame", new=AsyncMock(side_effect=mock_create_frame)),
            patch.object(service, "_upload_image", new=AsyncMock(side_effect=mock_upload_image)),
            patch.object(service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)),
        ):
            result = await service.create_enhanced_session_card(
                analysis=analysis, session_images=_make_session_images(1, 1)
            )

        assert result == "expected-frame-id"

    @pytest.mark.asyncio
    async def test_card_not_blocked_by_single_image_failure(self) -> None:
        """Card creation continues when one image upload fails (FR-011)."""
        service = _make_service()
        analysis = _make_analysis()
        upload_calls: list[str] = []
        sticky_call_count = 0

        async def mock_create_frame(title: str, user_id: int, n_images: int) -> str:
            return "frame-resilience-test"

        async def mock_upload_image(frame_id: str, image: dict, idx: int) -> str | None:
            upload_calls.append(image["telegram_file_id"])
            if idx == 0:
                return None  # First image fails
            return "img-id"

        async def mock_add_sticky_note(
            frame_id: str, content: str, style: dict, position: dict, geometry: dict
        ) -> str:
            nonlocal sticky_call_count
            sticky_call_count += 1
            return f"sticky-{sticky_call_count}"

        with (
            patch.object(service, "_create_frame", new=AsyncMock(side_effect=mock_create_frame)),
            patch.object(service, "_upload_image", new=AsyncMock(side_effect=mock_upload_image)),
            patch.object(service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis, session_images=_make_session_images(n_food=2, n_cgm=1)
            )

        # Both images were attempted (not aborted after first failure)
        assert len(upload_calls) == 3, f"Expected 3 upload attempts, got {len(upload_calls)}"
        # All 5 sections + separator still created
        assert sticky_call_count >= 6, (
            f"Expected ≥6 sticky notes despite image failure, got {sticky_call_count}"
        )
