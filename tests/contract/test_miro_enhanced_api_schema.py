"""Contract tests for Miro Enhanced API schema — feature 002 (T013).

Validates frame creation, image upload, and sticky-note creation endpoints
per contracts/miro-enhanced-api-schema.md.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from glucotrack.services.miro_service import MiroService

BOARD_ID = "board-enhanced-001"


def _make_analysis(user_id: int = 99) -> MagicMock:
    analysis = MagicMock()
    analysis.id = "analysis-uuid-enhanced"
    analysis.user_id = user_id
    analysis.session_id = "session-uuid-enhanced"
    analysis.nutrition_json = json.dumps(
        {
            "carbs_g": 45,
            "proteins_g": 20,
            "fats_g": 10,
            "gi_estimate": 65,
            "gi_category": "medium",
            "food_items": ["brown rice", "chicken"],
            "glucose_impact_narrative": "Gradual rise within 70–140 mg/dL.",
            "notes": "",
        }
    )
    analysis.glucose_curve_json = json.dumps(
        [
            {
                "timing_label": "1h after",
                "estimated_value_mg_dl": 130,
                "in_range": True,
                "notes": "",
                "curve_shape_label": "gradual rise",
            }
        ]
    )
    analysis.correlation_json = json.dumps(
        {
            "spikes": ["Rice caused 1h spike"],
            "dips": [],
            "stable_zones": [],
            "summary": "The rice meal caused a moderate spike.",
        }
    )
    analysis.recommendations_json = json.dumps(
        [{"priority": 1, "text": "Reduce rice portion"}]
    )
    analysis.activity_json = json.dumps(
        {
            "description": "30-min walk",
            "glucose_modulation": "reduced spike",
            "effect_summary": "moderate lowering",
        }
    )
    analysis.within_target_notes = "Within range."
    analysis.created_at = MagicMock()
    analysis.created_at.strftime = MagicMock(return_value="2026-04-23 10:00 UTC")
    return analysis


def _session_images() -> list[dict]:
    return [
        {"type": "food", "file_bytes": b"food_image_bytes", "telegram_file_id": "tg_food_1"},
        {"type": "cgm", "file_bytes": b"cgm_image_bytes", "telegram_file_id": "tg_cgm_1"},
    ]


class TestMiroEnhancedAPISchemaContract:
    """Contract tests per miro-enhanced-api-schema.md — frame, images, sticky notes."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_frame_creation_endpoint_and_body_shape(self) -> None:
        """Frame POST hits the correct endpoint with required body fields."""
        service = MiroService(access_token="tok", board_id=BOARD_ID, _retry_delays=())
        analysis = _make_analysis()
        captured: dict = {}

        def capture_frame(request: httpx.Request) -> httpx.Response:
            captured["frame_body"] = json.loads(request.content)
            return httpx.Response(
                201,
                json={"id": "frame-001", "type": "frame", "data": {"title": "..."}, "links": {}},
            )

        def capture_image(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                201,
                json={"id": "img-001", "type": "image", "data": {}, "parent": {"id": "frame-001"}},
            )

        def capture_sticky(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                201,
                json={"id": "sticky-001", "type": "sticky_note", "data": {}},
            )

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/frames").mock(
            side_effect=capture_frame
        )
        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/images").mock(
            side_effect=capture_image
        )
        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/sticky_notes").mock(
            side_effect=capture_sticky
        )

        await service.create_enhanced_session_card(
            analysis=analysis, session_images=_session_images()
        )

        body = captured["frame_body"]
        assert "data" in body
        assert "title" in body["data"]
        assert body["data"].get("format") == "custom"
        assert body["geometry"]["width"] == 1200

    @pytest.mark.asyncio
    @respx.mock
    async def test_image_upload_includes_parent_frame_id(self) -> None:
        """Image items are uploaded as children of the created frame."""
        service = MiroService(access_token="tok", board_id=BOARD_ID, _retry_delays=())
        analysis = _make_analysis()
        image_data_fields: list[dict] = []

        def capture_frame(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                201,
                json={"id": "frame-xyz", "type": "frame", "data": {}, "links": {}},
            )

        def capture_image(request: httpx.Request) -> httpx.Response:
            # Parse multipart to extract the JSON 'data' field
            content_type = request.headers.get("content-type", "")
            if "multipart" in content_type:
                # Extract boundary and parse — just check parent.id via raw content
                raw = request.content.decode("latin-1")
                # Find JSON data part
                for part in raw.split("--"):
                    if '"parent"' in part or '"position"' in part:
                        # Extract JSON blob
                        lines = part.strip().split("\r\n")
                        for i, line in enumerate(lines):
                            if line.startswith("{") or (i > 0 and lines[i - 1] == ""):
                                try:
                                    data_dict = json.loads(line)
                                    image_data_fields.append(data_dict)
                                    break
                                except json.JSONDecodeError:
                                    pass
            return httpx.Response(
                201,
                json={"id": "img-001", "type": "image", "data": {}, "parent": {"id": "frame-xyz"}},
            )

        def capture_sticky(request: httpx.Request) -> httpx.Response:
            return httpx.Response(201, json={"id": "sticky-001", "type": "sticky_note", "data": {}})

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/frames").mock(
            side_effect=capture_frame
        )
        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/images").mock(
            side_effect=capture_image
        )
        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/sticky_notes").mock(
            side_effect=capture_sticky
        )

        frame_id = await service.create_enhanced_session_card(
            analysis=analysis, session_images=_session_images()
        )
        # At minimum: frame ID returned and image endpoint was called
        assert frame_id == "frame-xyz"
        assert respx.calls.call_count >= 3  # frame + images + sticky notes

    @pytest.mark.asyncio
    @respx.mock
    async def test_sticky_notes_have_parent_frame_id(self) -> None:
        """All sticky notes reference the created frame via parent.id."""
        service = MiroService(access_token="tok", board_id=BOARD_ID, _retry_delays=())
        analysis = _make_analysis()
        captured_sticky_bodies: list[dict] = []

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/frames").mock(
            return_value=httpx.Response(
                201, json={"id": "frame-sticky-test", "type": "frame", "data": {}, "links": {}}
            )
        )
        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/images").mock(
            return_value=httpx.Response(
                201,
                json={"id": "img-001", "type": "image", "data": {}, "parent": {"id": "frame-sticky-test"}},
            )
        )

        def capture_sticky(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            captured_sticky_bodies.append(body)
            return httpx.Response(201, json={"id": "sticky-001", "type": "sticky_note", "data": {}})

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/sticky_notes").mock(
            side_effect=capture_sticky
        )

        await service.create_enhanced_session_card(
            analysis=analysis, session_images=_session_images()
        )

        # All sticky notes must have parent.id = frame ID
        assert len(captured_sticky_bodies) >= 6, (
            f"Expected ≥6 sticky notes (separator + 5 sections), got {len(captured_sticky_bodies)}"
        )
        for body in captured_sticky_bodies:
            assert body.get("parent", {}).get("id") == "frame-sticky-test", (
                f"Sticky note missing parent.id: {body}"
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_sticky_note_style_uses_valid_fill_color(self) -> None:
        """Sticky note style must use a valid fillColor enum value, never a hex code.

        StickyNoteStyle.fillColor is a STRICT ENUM — only named values are accepted.
        Hex codes like '#e6e6e6' cause 400 Bad Request. textColor is also an
        invalid field for sticky notes and must not be present.
        Valid values: gray, light_yellow, yellow, orange, light_green, green,
        dark_green, cyan, light_pink, pink, violet, red, light_blue, blue,
        dark_blue, black.
        """
        _VALID_FILL_COLORS = {
            "gray", "light_yellow", "yellow", "orange", "light_green", "green",
            "dark_green", "cyan", "light_pink", "pink", "violet", "red",
            "light_blue", "blue", "dark_blue", "black",
        }
        service = MiroService(access_token="tok", board_id=BOARD_ID, _retry_delays=())
        analysis = _make_analysis()
        captured_styles: list[dict] = []

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/frames").mock(
            return_value=httpx.Response(
                201, json={"id": "frame-style-test", "type": "frame", "data": {}, "links": {}}
            )
        )
        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/images").mock(
            return_value=httpx.Response(
                201,
                json={"id": "img-001", "type": "image", "data": {}, "parent": {"id": "frame-style-test"}},
            )
        )

        def capture_sticky(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            if "style" in body:
                captured_styles.append(body["style"])
            return httpx.Response(201, json={"id": "sn-001", "type": "sticky_note", "data": {}})

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/sticky_notes").mock(
            side_effect=capture_sticky
        )

        await service.create_enhanced_session_card(
            analysis=analysis, session_images=_session_images()
        )

        assert len(captured_styles) >= 1, "No sticky notes captured"
        for style in captured_styles:
            assert "textColor" not in style, (
                f"'textColor' is not a valid Miro sticky note style field — got: {style}"
            )
            fill = style.get("fillColor")
            assert fill in _VALID_FILL_COLORS, (
                f"fillColor must be a named enum value, not a hex code — got: {fill!r}. "
                f"Valid values: {sorted(_VALID_FILL_COLORS)}"
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_sticky_note_position_has_no_relativeto(self) -> None:
        """Sticky note position must NOT include relativeTo, and must use frame-relative coords.

        PositionChange schema has no relativeTo field. When parent.id is set, Miro
        treats x,y as frame-relative (from frame top-left, item center at x,y) —
        the same convention as the multipart image upload endpoint. Coordinates
        must be positive and within the 1200px-wide frame.
        """
        service = MiroService(access_token="tok", board_id=BOARD_ID, _retry_delays=())
        analysis = _make_analysis()
        captured_positions: list[dict] = []

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/frames").mock(
            return_value=httpx.Response(
                201, json={"id": "frame-pos-test", "type": "frame", "data": {}, "links": {}}
            )
        )
        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/images").mock(
            return_value=httpx.Response(
                201,
                json={"id": "img-001", "type": "image", "data": {}, "parent": {"id": "frame-pos-test"}},
            )
        )

        def capture_sticky(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            if "position" in body:
                captured_positions.append(body["position"])
            return httpx.Response(201, json={"id": "sn-001", "type": "sticky_note", "data": {}})

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/sticky_notes").mock(
            side_effect=capture_sticky
        )

        await service.create_enhanced_session_card(
            analysis=analysis, session_images=_session_images()
        )

        assert len(captured_positions) >= 1, "No sticky notes captured"
        for pos in captured_positions:
            assert "relativeTo" not in pos, (
                f"Sticky notes must not include relativeTo (unsupported field) — got: {pos}"
            )
            # Frame-relative coords: x=600 centres horizontally in 1200px frame, y > 0
            assert pos.get("x", 0) > 0, f"Expected positive frame-relative x — got: {pos}"
            assert pos.get("y", 0) > 0, f"Expected positive frame-relative y — got: {pos}"
            assert pos.get("x", 0) <= 1200, f"x must be within frame width 1200 — got: {pos}"

    @pytest.mark.asyncio
    @respx.mock
    async def test_sticky_note_geometry_has_width_only(self) -> None:
        """Sticky note geometry must only set width, not height.

        FixedRatioNoRotationGeometry accepts either width OR height, not both.
        Passing both causes a 400 Bad Request from the Miro API.
        """
        service = MiroService(access_token="tok", board_id=BOARD_ID, _retry_delays=())
        analysis = _make_analysis()
        captured_geometries: list[dict] = []

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/frames").mock(
            return_value=httpx.Response(
                201, json={"id": "frame-geom-test", "type": "frame", "data": {}, "links": {}}
            )
        )
        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/images").mock(
            return_value=httpx.Response(
                201,
                json={"id": "img-001", "type": "image", "data": {}, "parent": {"id": "frame-geom-test"}},
            )
        )

        def capture_sticky(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            if "geometry" in body:
                captured_geometries.append(body["geometry"])
            return httpx.Response(201, json={"id": "sn-001", "type": "sticky_note", "data": {}})

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/sticky_notes").mock(
            side_effect=capture_sticky
        )

        await service.create_enhanced_session_card(
            analysis=analysis, session_images=_session_images()
        )

        assert len(captured_geometries) >= 1, "No sticky notes captured"
        for geom in captured_geometries:
            assert "width" in geom, f"Sticky note geometry must include width — got: {geom}"
            assert "height" not in geom, (
                f"Sticky note geometry must not include height "
                f"(FixedRatioNoRotationGeometry cannot set both) — got: {geom}"
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_frame_id(self) -> None:
        """create_enhanced_session_card returns the frame ID from step 1."""
        service = MiroService(access_token="tok", board_id=BOARD_ID, _retry_delays=())
        analysis = _make_analysis()

        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/frames").mock(
            return_value=httpx.Response(
                201, json={"id": "the-frame-id", "type": "frame", "data": {}, "links": {}}
            )
        )
        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/images").mock(
            return_value=httpx.Response(
                201,
                json={"id": "img-001", "type": "image", "data": {}, "parent": {"id": "the-frame-id"}},
            )
        )
        respx.post(f"https://api.miro.com/v2/boards/{BOARD_ID}/sticky_notes").mock(
            return_value=httpx.Response(201, json={"id": "sn-001", "type": "sticky_note", "data": {}})
        )

        result = await service.create_enhanced_session_card(
            analysis=analysis, session_images=_session_images()
        )
        assert result == "the-frame-id"
