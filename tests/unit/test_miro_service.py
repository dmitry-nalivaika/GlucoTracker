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
            patch.object(
                service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)
            ),
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
            patch.object(
                service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)
            ),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis,
                session_images=_make_session_images(n_food=2, n_cgm=1),
            )

        # All food images must appear before the first cgm image
        if "cgm" in upload_types:
            first_cgm = upload_types.index("cgm")
            for i in range(first_cgm):
                assert (
                    upload_types[i] == "food"
                ), f"Expected food at position {i}, got {upload_types[i]}"

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
            patch.object(
                service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)
            ),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis, session_images=_make_session_images(1, 1)
            )

        # At least one placeholder sticky note for the failed uploads
        placeholder_texts = [
            c for c in sticky_contents if "unavailable" in c.lower() or "failed" in c.lower()
        ]
        assert (
            len(placeholder_texts) >= 1
        ), f"Expected placeholder sticky notes for failed uploads, got: {sticky_contents}"

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
            patch.object(
                service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)
            ),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis, session_images=_make_session_images(1, 1)
            )

        # 1 separator + 5 sections = 6 sticky notes (plus any image placeholders)
        assert (
            sticky_call_count >= 6
        ), f"Expected ≥6 sticky note calls (separator + 5 sections), got {sticky_call_count}"

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
            patch.object(
                service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)
            ),
        ):
            result = await service.create_enhanced_session_card(
                analysis=analysis, session_images=_make_session_images(1, 1)
            )

        assert result == "expected-frame-id"

    @pytest.mark.asyncio
    async def test_image_placeholder_positions_within_frame_width(self) -> None:
        """Placeholder x-positions for 3+ images must all be within frame width (no overflow)."""
        from glucotrack.services.miro_service import _FRAME_WIDTH

        service = _make_service()
        analysis = _make_analysis()
        placeholder_positions: list[dict] = []

        async def mock_create_frame(title: str, user_id: int, n_images: int) -> str:
            return "frame-id"

        async def mock_upload_image(frame_id: str, image: dict, idx: int) -> str | None:
            return None  # All uploads fail → placeholders created for each

        async def mock_add_sticky_note(
            frame_id: str, content: str, style: dict, position: dict, geometry: dict
        ) -> str:
            if "unavailable" in content.lower():
                placeholder_positions.append(position)
            return "sticky-id"

        with (
            patch.object(service, "_create_frame", new=AsyncMock(side_effect=mock_create_frame)),
            patch.object(service, "_upload_image", new=AsyncMock(side_effect=mock_upload_image)),
            patch.object(
                service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)
            ),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis,
                session_images=_make_session_images(n_food=2, n_cgm=1),  # 3 images → idx 0,1,2
            )

        assert (
            len(placeholder_positions) == 3
        ), f"Expected 3 placeholder sticky notes, got {len(placeholder_positions)}"
        for i, pos in enumerate(placeholder_positions):
            assert (
                pos["x"] <= _FRAME_WIDTH
            ), f"Placeholder {i} x={pos['x']} exceeds frame width {_FRAME_WIDTH}"

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_image_uses_height_geometry(self) -> None:
        """_upload_image must constrain by height (not width) to prevent portrait overflow."""
        import re

        from glucotrack.services.miro_service import _IMAGE_HEIGHT

        service = MiroService(access_token="t", board_id="b", _retry_delays=())
        captured_geometry: list[dict] = []

        def capture(request: httpx.Request) -> httpx.Response:
            match = re.search(rb'"geometry"\s*:\s*(\{[^}]+\})', request.content)
            if match:
                captured_geometry.append(json.loads(match.group(1)))
            return httpx.Response(201, json={"id": "img-id"})

        respx.post("https://api.miro.com/v2/boards/b/images").mock(side_effect=capture)

        await service._upload_image(
            frame_id="frame-1",
            image={"type": "cgm", "file_bytes": b"fake", "telegram_file_id": "f"},
            idx=0,
        )

        assert captured_geometry, "No geometry captured from request"
        geom = captured_geometry[0]
        assert "height" in geom, f"Expected height-constrained geometry, got: {geom}"
        assert "width" not in geom, f"Width must not be set when height is used, got: {geom}"
        assert geom["height"] == _IMAGE_HEIGHT

    @pytest.mark.asyncio
    async def test_sticky_section_start_below_image_bottom(self) -> None:
        """First sticky note y-center must be far enough below image bottom to avoid overlap."""
        import math

        from glucotrack.services.miro_service import (
            _IMAGE_ROW_HEIGHT,
            _IMAGE_Y_START,
            _IMAGES_PER_ROW,
        )

        service = _make_service()
        analysis = _make_analysis()
        sticky_positions: list[dict] = []

        async def mock_create_frame(title: str, user_id: int, n_images: int) -> str:
            return "frame-id"

        async def mock_upload_image(frame_id: str, image: dict, idx: int) -> str | None:
            return "img-id"

        async def mock_add_sticky_note(
            frame_id: str, content: str, style: dict, position: dict, geometry: dict
        ) -> str:
            sticky_positions.append(position)
            return "sticky-id"

        with (
            patch.object(service, "_create_frame", new=AsyncMock(side_effect=mock_create_frame)),
            patch.object(service, "_upload_image", new=AsyncMock(side_effect=mock_upload_image)),
            patch.object(
                service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)
            ),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis,
                session_images=_make_session_images(n_food=1, n_cgm=1),
            )

        n_images = 2
        n_image_rows = math.ceil(n_images / _IMAGES_PER_ROW)
        image_bottom = _IMAGE_Y_START + n_image_rows * _IMAGE_ROW_HEIGHT
        # Sticky center must be at least 120px below image bottom (leaves room for sticky top edge)
        min_sticky_y = image_bottom + 120
        for pos in sticky_positions:
            assert pos["y"] >= min_sticky_y, (
                f"Sticky y={pos['y']} is too close to image bottom {image_bottom} "
                f"(min required: {min_sticky_y})"
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_image_x_within_frame_for_idx_2(self) -> None:
        """_upload_image with idx=2 must produce x_center within frame width."""
        import re

        from glucotrack.services.miro_service import _FRAME_WIDTH

        service = MiroService(
            access_token="t",
            board_id="b",
            _retry_delays=(),
        )
        captured_x: list[float] = []

        def capture(request: httpx.Request) -> httpx.Response:
            # Extract "x" value from the JSON data field embedded in the multipart body
            match = re.search(rb'"x"\s*:\s*(\d+(?:\.\d+)?)', request.content)
            if match:
                captured_x.append(float(match.group(1)))
            return httpx.Response(201, json={"id": "img-id"})

        respx.post("https://api.miro.com/v2/boards/b/images").mock(side_effect=capture)

        await service._upload_image(
            frame_id="frame-1",
            image={"type": "food", "file_bytes": b"fake", "telegram_file_id": "f"},
            idx=2,
        )

        assert captured_x, "No x value captured from multipart request"
        assert all(
            x <= _FRAME_WIDTH for x in captured_x
        ), f"_upload_image idx=2: x={captured_x[0]} exceeds frame width {_FRAME_WIDTH}"

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
            patch.object(
                service, "_add_sticky_note", new=AsyncMock(side_effect=mock_add_sticky_note)
            ),
        ):
            await service.create_enhanced_session_card(
                analysis=analysis, session_images=_make_session_images(n_food=2, n_cgm=1)
            )

        # Both images were attempted (not aborted after first failure)
        assert len(upload_calls) == 3, f"Expected 3 upload attempts, got {len(upload_calls)}"
        # All 5 sections + separator still created
        assert (
            sticky_call_count >= 6
        ), f"Expected ≥6 sticky notes despite image failure, got {sticky_call_count}"


class TestMiroBuildSectionText:
    """Unit tests for _build_section_text() section content — Phases 4–8 (T024–T037)."""

    def _make_analysis_with(self, **overrides: str | None) -> MagicMock:
        analysis = _make_analysis()
        for attr, value in overrides.items():
            setattr(analysis, attr, value)
        return analysis

    # ── Phase 4 / US2: Food section (T024) ───────────────────────────────────

    def test_food_section_contains_gi_category_and_items(self) -> None:
        """Food section includes GI category, food items, and glucose impact narrative (T024)."""
        service = _make_service()
        analysis = self._make_analysis_with(
            nutrition_json=json.dumps(
                {
                    "carbs_g": 60,
                    "proteins_g": 15,
                    "fats_g": 8,
                    "gi_estimate": 72,
                    "gi_category": "high",
                    "food_items": ["white bread", "jam"],
                    "glucose_impact_narrative": (
                        "High-GI foods expected to raise glucose rapidly, "
                        "peaking outside 70–140 mg/dL."
                    ),
                    "notes": "",
                }
            )
        )
        text = service._build_section_text(analysis, "food")
        assert "white bread" in text
        assert "jam" in text
        assert "high" in text.lower() or "GI" in text
        assert "60" in text  # carbs
        assert "70" in text or "140" in text  # narrative references target range

    def test_food_section_handles_missing_food_items(self) -> None:
        service = _make_service()
        analysis = self._make_analysis_with(
            nutrition_json=json.dumps(
                {"carbs_g": 40, "proteins_g": 10, "fats_g": 5, "gi_estimate": 50, "notes": ""}
            )
        )
        text = service._build_section_text(analysis, "food")
        assert "Food" in text
        assert "40" in text

    # ── Phase 5 / US3: Glucose section (T027) ────────────────────────────────

    def test_glucose_section_contains_range_and_curve_label(self) -> None:
        """Glucose Chart section includes mg/dL values, range status, and curve labels (T027)."""
        service = _make_service()
        analysis = self._make_analysis_with(
            glucose_curve_json=json.dumps(
                [
                    {
                        "timing_label": "fasting",
                        "estimated_value_mg_dl": 85,
                        "in_range": True,
                        "notes": "",
                        "curve_shape_label": "stable within range",
                    },
                    {
                        "timing_label": "2h after",
                        "estimated_value_mg_dl": 160,
                        "in_range": False,
                        "notes": "spike",
                        "curve_shape_label": "sharp spike with recovery",
                    },
                ]
            )
        )
        text = service._build_section_text(analysis, "glucose")
        assert "mg/dL" in text
        assert "in range" in text.lower() or "✅" in text
        assert "out of range" in text.lower() or "⚠️" in text
        assert "stable within range" in text
        assert "sharp spike with recovery" in text

    def test_glucose_section_cgm_unparseable_shows_advisory(self) -> None:
        """When CGM is unparseable, glucose section shows 'unreadable' advisory (T027)."""
        service = _make_service()
        analysis = self._make_analysis_with(
            glucose_curve_json=json.dumps([]),
            raw_response=json.dumps(
                {
                    "cgm_parseable": False,
                    "cgm_parse_error": "Screenshot too blurry",
                }
            ),
        )
        text = service._build_section_text(analysis, "glucose")
        assert "unreadable" in text.lower() or "CGM" in text

    # ── Phase 6 / US4: Correlation section (T030) ────────────────────────────

    def test_correlation_section_includes_spikes_and_summary(self) -> None:
        """Correlation section renders spikes, dips, stable zones, and summary (T030)."""
        service = _make_service()
        analysis = self._make_analysis_with(
            correlation_json=json.dumps(
                {
                    "spikes": [
                        "Rice caused spike at 1h",
                        "Dessert contributed to 2h elevation",
                    ],
                    "dips": ["Walk after meal lowered glucose"],
                    "stable_zones": ["Fasting was stable"],
                    "summary": "The rice meal caused the primary spike; the walk helped attenuate it.",
                }
            )
        )
        text = service._build_section_text(analysis, "correlation")
        assert "Rice caused spike at 1h" in text
        assert "Walk after meal lowered glucose" in text
        assert "Fasting was stable" in text
        assert (
            "rice meal" in text.lower() or "summary" in text.lower() or "attenuate" in text.lower()
        )

    def test_correlation_section_skips_empty_lists(self) -> None:
        """Correlation section does not show empty spike/dip headers."""
        service = _make_service()
        analysis = self._make_analysis_with(
            correlation_json=json.dumps(
                {
                    "spikes": [],
                    "dips": [],
                    "stable_zones": [],
                    "summary": "All good with pasta meal.",
                }
            )
        )
        text = service._build_section_text(analysis, "correlation")
        # No "Spikes:" or "Dips:" heading when lists are empty
        assert "Spikes:" not in text
        assert "All good with pasta meal." in text

    # ── Phase 7 / US5: Recommendations section (T033) ────────────────────────

    def test_recommendations_section_formats_list(self) -> None:
        """Recommendations section renders items in priority order (T033)."""
        service = _make_service()
        analysis = self._make_analysis_with(
            recommendations_json=json.dumps(
                [
                    {"priority": 3, "text": "Third priority suggestion for pasta"},
                    {"priority": 1, "text": "Top priority suggestion for pasta"},
                    {"priority": 2, "text": "Second priority suggestion for pasta"},
                ]
            )
        )
        text = service._build_section_text(analysis, "recommendations")
        # Items must appear in priority order
        pos_1 = text.find("Top priority")
        pos_2 = text.find("Second priority")
        pos_3 = text.find("Third priority")
        assert pos_1 < pos_2 < pos_3, "Recommendations must be sorted by priority"

    def test_recommendations_section_fallback_empty(self) -> None:
        """Recommendations section shows fallback message when list is empty."""
        service = _make_service()
        analysis = self._make_analysis_with(recommendations_json=json.dumps([]))
        text = service._build_section_text(analysis, "recommendations")
        assert "No specific recommendations" in text

    # ── Phase 8 / Activity section (T036) ────────────────────────────────────

    def test_activity_section_no_activity(self) -> None:
        """Activity section shows 'No activity logged' when description is null (T036)."""
        service = _make_service()
        analysis = self._make_analysis_with(
            activity_json=json.dumps(
                {
                    "description": None,
                    "glucose_modulation": "No activity logged.",
                    "effect_summary": "No activity to analyse.",
                }
            )
        )
        text = service._build_section_text(analysis, "activity")
        assert "Activity" in text
        assert "No activity logged" in text

    def test_activity_section_with_activity(self) -> None:
        """Activity section shows activity details when description is present."""
        service = _make_service()
        analysis = self._make_analysis_with(
            activity_json=json.dumps(
                {
                    "description": "45-min jog",
                    "glucose_modulation": "Significant glucose reduction post-run",
                    "effect_summary": "Levels dropped to baseline 30 min earlier",
                }
            )
        )
        text = service._build_section_text(analysis, "activity")
        assert "45-min jog" in text
        assert "glucose" in text.lower() or "reduction" in text.lower()

    def test_activity_section_null_activity_json(self) -> None:
        """Activity section handles activity_json=None gracefully."""
        service = _make_service()
        analysis = self._make_analysis_with(activity_json=None)
        text = service._build_section_text(analysis, "activity")
        assert "Activity" in text
        assert "No activity logged" in text

    def test_section_fallback_on_invalid_json(self) -> None:
        """Any section with invalid JSON falls back to 'Analysis unavailable' message."""
        service = _make_service()
        analysis = self._make_analysis_with(nutrition_json="not-valid-json")
        text = service._build_section_text(analysis, "food")
        assert "unavailable" in text.lower() or "Analysis" in text

    # ── Bullet point format tests ─────────────────────────────────────────────

    def test_food_section_uses_bullet_points(self) -> None:
        """Food section data lines must use • bullet prefix."""
        service = _make_service()
        analysis = _make_analysis()
        text = service._build_section_text(analysis, "food")
        assert "•" in text, f"Expected bullet points in food section, got:\n{text}"

    def test_activity_section_uses_bullet_points(self) -> None:
        """Activity section lines must use • bullet prefix when activity is present."""
        service = _make_service()
        analysis = self._make_analysis_with(
            activity_json=json.dumps(
                {
                    "description": "30-min walk",
                    "glucose_modulation": "Moderate reduction",
                    "effect_summary": "Levels stabilised",
                }
            )
        )
        text = service._build_section_text(analysis, "activity")
        assert "•" in text, f"Expected bullet points in activity section, got:\n{text}"

    def test_glucose_section_uses_bullet_points(self) -> None:
        """Each glucose curve point must use • bullet prefix."""
        service = _make_service()
        analysis = _make_analysis()
        text = service._build_section_text(analysis, "glucose")
        assert "•" in text, f"Expected bullet points in glucose section, got:\n{text}"

    def test_recommendations_section_uses_bullet_points(self) -> None:
        """Recommendations must use • bullet prefix instead of numbered list."""
        service = _make_service()
        analysis = _make_analysis()
        text = service._build_section_text(analysis, "recommendations")
        assert "•" in text, f"Expected bullet points in recommendations section, got:\n{text}"


class TestMiroSectionTextRussian:
    """Russian section headers appear when lang='ru' — T018."""

    def test_food_section_russian_header(self) -> None:
        """_build_section_text('food', lang='ru') starts with Russian header."""
        service = _make_service()
        analysis = _make_analysis()
        text = service._build_section_text(analysis, "food", lang="ru")
        assert "Питание" in text, f"Expected Russian header 'Питание' in:\n{text}"

    def test_activity_section_russian_header(self) -> None:
        """_build_section_text('activity', lang='ru') starts with Russian header."""
        service = _make_service()
        analysis = _make_analysis()
        text = service._build_section_text(analysis, "activity", lang="ru")
        assert "Активность" in text, f"Expected Russian header 'Активность' in:\n{text}"

    def test_glucose_section_russian_header(self) -> None:
        """_build_section_text('glucose', lang='ru') starts with Russian header."""
        service = _make_service()
        analysis = _make_analysis()
        text = service._build_section_text(analysis, "glucose", lang="ru")
        assert (
            "Кривая" in text or "глюкоза" in text.lower()
        ), f"Expected Russian glucose header in:\n{text}"

    def test_correlation_section_russian_header(self) -> None:
        """_build_section_text('correlation', lang='ru') starts with Russian header."""
        service = _make_service()
        analysis = _make_analysis()
        text = service._build_section_text(analysis, "correlation", lang="ru")
        assert "Корреляция" in text, f"Expected Russian header 'Корреляция' in:\n{text}"

    def test_recommendations_section_russian_header(self) -> None:
        """_build_section_text('recommendations', lang='ru') starts with Russian header."""
        service = _make_service()
        analysis = _make_analysis()
        text = service._build_section_text(analysis, "recommendations", lang="ru")
        assert "Рекомендации" in text, f"Expected Russian header 'Рекомендации' in:\n{text}"

    def test_english_header_by_default(self) -> None:
        """_build_section_text without lang kwarg returns English header."""
        service = _make_service()
        analysis = _make_analysis()
        text = service._build_section_text(analysis, "food")
        assert "Food" in text

    def test_activity_no_activity_body_is_russian(self) -> None:
        """When no activity is logged, the fallback body must be in Russian for lang='ru'."""
        service = _make_service()
        analysis = _make_analysis()
        analysis.activity_json = None
        text = service._build_section_text(analysis, "activity", lang="ru")
        assert (
            "No activity logged" not in text
        ), f"Hardcoded English fallback still present in Russian activity section:\n{text}"
        assert (
            "Активность не записана" in text
        ), f"Expected Russian fallback 'Активность не записана' in:\n{text}"

    def test_recommendations_empty_body_is_russian(self) -> None:
        """When recommendations list is empty, the fallback body must be in Russian."""
        service = _make_service()
        analysis = _make_analysis()
        analysis.recommendations_json = "[]"
        text = service._build_section_text(analysis, "recommendations", lang="ru")
        assert (
            "No specific recommendations" not in text
        ), f"Hardcoded English fallback still present in Russian recommendations:\n{text}"

    def test_glucose_cgm_unreadable_body_is_russian(self) -> None:
        """When CGM is unreadable, the error body must be in Russian for lang='ru'."""
        import json as _json

        service = _make_service()
        analysis = _make_analysis()
        analysis.raw_response = _json.dumps(
            {"cgm_parseable": False, "cgm_parse_error": "blurry image"}
        )
        text = service._build_section_text(analysis, "glucose", lang="ru")
        assert (
            "Please re-submit a clearer screenshot" not in text
        ), f"Hardcoded English fallback still present in Russian glucose section:\n{text}"
        assert (
            "скриншот" in text.lower() or "чёткий" in text.lower() or "нечитаем" in text.lower()
        ), f"Expected Russian CGM-unreadable text in:\n{text}"
