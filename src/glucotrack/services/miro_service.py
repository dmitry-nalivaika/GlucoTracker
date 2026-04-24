"""MiroService — Miro REST API integration.

Isolated per Constitution III: "storage behind StorageRepository;
input channels behind adapter." Miro is an output channel.

FR-009: Miro failure MUST NOT block Telegram delivery.
Contract: contracts/miro-api-schema.md / miro-enhanced-api-schema.md
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
from typing import Any

import httpx

from glucotrack.bot.i18n import t as _t

logger = logging.getLogger(__name__)

_MIRO_API_BASE = "https://api.miro.com/v2"
# Default exponential backoff delays (seconds) for 5xx retries
_DEFAULT_RETRY_DELAYS: tuple[float, ...] = (1.0, 2.0, 4.0)

# ── Enhanced card layout constants ────────────────────────────────────────────
_FRAME_WIDTH = 1200
_IMAGE_WIDTH = 560  # two large images side-by-side
_IMAGE_HEIGHT = 400
_IMAGES_PER_ROW = 2
_IMAGE_ROW_HEIGHT = 450
_IMAGE_Y_START = 40
_IMAGE_X_STEP = 600  # column stride: 0→x=300, 1→x=900
_SECTION_COLS = 2  # 2-column sticky note grid
_SECTION_WIDTH = 540  # half-frame-width notes (~540px per column)
_SECTION_HEIGHT = 280  # row-to-row spacing between section centres
_SECTION_GAP = 30
# Padding from the bottom of the last image row to the first sticky note centre.
# Must be large enough that the sticky top edge (centre − ~150px half-height) clears
# the image bottom, even for tall/portrait images capped at _IMAGE_HEIGHT.
_SECTION_TOP_MARGIN = 180

# Section colour palette (feature 002)
# Miro StickyNoteStyle.fillColor is a STRICT ENUM — only named values accepted.
# Hex codes like "#e6e6e6" cause 400 Bad Request.
# Valid values: gray, light_yellow, yellow, orange, light_green, green, dark_green,
#               cyan, light_pink, pink, violet, red, light_blue, blue, dark_blue, black
_STYLE_SEPARATOR = {"fillColor": "gray"}
_STYLE_SECTION = {"fillColor": "light_yellow"}
_STYLE_PLACEHOLDER = {"fillColor": "yellow"}


class MiroError(Exception):
    """Raised when Miro API call fails and is non-retryable (or retries exhausted)."""


class MiroService:
    """Creates cards on a Miro board from AIAnalysis results.

    Retry strategy per miro-api-schema.md:
    - 4xx: fail immediately, no retry
    - 429: retry after Retry-After header (up to 3×)
    - 5xx: retry with exponential backoff (1s, 2s, 4s; up to 3×)
    """

    def __init__(
        self,
        access_token: str,
        board_id: str,
        _retry_delays: tuple[float, ...] = _DEFAULT_RETRY_DELAYS,
    ) -> None:
        self._access_token = access_token
        self._board_id = board_id
        self._retry_delays = _retry_delays
        self.board_id = board_id  # public for consumers

    def _anonymise_user_id(self, user_id: int) -> str:
        """Return a short hash of user_id — NEVER expose raw telegram_user_id."""
        digest = hashlib.sha256(str(user_id).encode()).hexdigest()[:8]
        return digest

    def _build_description(self, analysis: Any) -> str:
        """Build Miro card description from AIAnalysis fields."""
        nutrition = json.loads(analysis.nutrition_json)
        glucose_curve = json.loads(analysis.glucose_curve_json)
        correlation = json.loads(analysis.correlation_json)
        recommendations = json.loads(analysis.recommendations_json)

        carbs = nutrition.get("carbs_g", "?")
        proteins = nutrition.get("proteins_g", "?")
        fats = nutrition.get("fats_g", "?")
        gi = nutrition.get("gi_estimate", "?")

        glucose_summary = (
            "; ".join(
                f"{p['timing_label']}: {p.get('estimated_value_mg_dl', '?')} mg/dL"
                for p in glucose_curve
            )
            or "No data"
        )

        correlation_summary = correlation.get("summary", "")
        top_rec = recommendations[0]["text"] if recommendations else "None"

        return (
            f"**Nutrition**: {carbs}g carbs, {proteins}g protein, {fats}g fat, GI ~{gi}\n\n"
            f"**Glucose Response**: {glucose_summary}\n\n"
            f"**Correlation**: {correlation_summary}\n\n"
            f"**Top Recommendation**: {top_rec}"
        )

    def _build_payload(self, analysis: Any) -> dict[str, Any]:
        """Build the full POST body for Miro cards endpoint."""
        anon_id = self._anonymise_user_id(analysis.user_id)
        try:
            timestamp = analysis.created_at.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            timestamp = "unknown time"

        title = f"GlucoTrack Session — {timestamp} [User #{anon_id}]"
        description = self._build_description(analysis)

        return {
            "data": {"title": title, "description": description},
            "position": {"x": 0, "y": 0, "origin": "center"},
            "geometry": {"width": 320, "height": 180},
        }

    async def create_session_card(self, analysis: Any) -> str:
        """Create a Miro session card for the given AIAnalysis.

        Returns:
            miro_card_id from the 201 response.

        Raises:
            MiroError: on 4xx or retries exhausted.
        """
        url = f"{_MIRO_API_BASE}/boards/{self._board_id}/cards"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = self._build_payload(analysis)

        async with httpx.AsyncClient() as client:
            # 429 and 5xx share retry budget; independent counters per contract
            retry_delays = list(self._retry_delays)

            for attempt in range(len(retry_delays) + 1):
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 201:
                    data: dict[str, Any] = response.json()
                    return str(data["id"])

                if response.status_code == 429:
                    if attempt >= len(retry_delays):
                        raise MiroError(f"Miro rate limit exceeded after {attempt} retries: 429")
                    wait = float(response.headers.get("Retry-After", retry_delays[attempt]))
                    logger.warning(
                        "Miro 429 rate limit — retrying in %.1fs (attempt %d)",
                        wait,
                        attempt + 1,
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code >= 500:
                    if attempt >= len(retry_delays):
                        raise MiroError(
                            f"Miro server error after {attempt} retries: {response.status_code}"
                        )
                    wait = retry_delays[attempt]
                    logger.warning(
                        "Miro %d server error — retrying in %.1fs (attempt %d)",
                        response.status_code,
                        wait,
                        attempt + 1,
                    )
                    await asyncio.sleep(wait)
                    continue

                # 4xx: fail immediately, no retry
                raise MiroError(f"Miro API error {response.status_code}: {response.text[:200]}")

        # Unreachable but satisfies type checker
        raise MiroError("Miro card creation failed — no successful response")

    # ── Enhanced card helpers (feature 002) ───────────────────────────────────

    async def _create_frame(self, title: str, user_id: int, n_images: int) -> str:
        """Create a Miro Frame container.

        Returns the frame ID from the 201 response.
        Raises MiroError on unrecoverable failure.
        """
        n_image_rows = math.ceil(n_images / _IMAGES_PER_ROW) if n_images > 0 else 0
        n_section_rows = 3  # fixed 2×3 grid: (food|glucose), (recs|correlation), (activity|header)
        section_block = n_section_rows * (_SECTION_HEIGHT + _SECTION_GAP)
        frame_height = (
            _IMAGE_Y_START
            + n_image_rows * _IMAGE_ROW_HEIGHT
            + _SECTION_TOP_MARGIN
            + section_block
            + 100  # bottom margin below last sticky note
        )

        url = f"{_MIRO_API_BASE}/boards/{self._board_id}/frames"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload: dict[str, Any] = {
            "data": {"title": title, "format": "custom", "type": "freeform"},
            "position": {"x": 0, "y": 0, "origin": "center"},
            "geometry": {"width": _FRAME_WIDTH, "height": frame_height},
        }

        async with httpx.AsyncClient() as client:
            retry_delays = list(self._retry_delays)
            for attempt in range(len(retry_delays) + 1):
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 201:
                    return str(response.json()["id"])
                if response.status_code == 429:
                    if attempt >= len(retry_delays):
                        raise MiroError("Miro rate limit exceeded creating frame")
                    retry_after = float(response.headers.get("Retry-After", retry_delays[attempt]))
                    await asyncio.sleep(retry_after)
                    continue
                if response.status_code >= 500:
                    if attempt >= len(retry_delays):
                        raise MiroError(f"Miro server error creating frame: {response.status_code}")
                    await asyncio.sleep(retry_delays[attempt])
                    continue
                raise MiroError(
                    f"Miro frame creation failed {response.status_code}: {response.text[:200]}"
                )
        raise MiroError("Miro frame creation failed — no successful response")

    async def _upload_image(self, frame_id: str, image: dict[str, Any], idx: int) -> str | None:
        """Upload a single image as a child item of the frame.

        Returns image item ID on success, None on failure (FR-011).
        """
        # Miro uses origin:center — compute row/col to support multiple rows of images
        col = idx % _IMAGES_PER_ROW
        row = idx // _IMAGES_PER_ROW
        x_center = _IMAGE_X_STEP * col + 20 + _IMAGE_WIDTH // 2
        y_center = _IMAGE_Y_START + row * _IMAGE_ROW_HEIGHT + _IMAGE_HEIGHT // 2
        data_field = json.dumps(
            {
                "title": f"{image['type']}_{idx + 1}",
                "position": {"x": x_center, "y": y_center},
                # Use height constraint so portrait images (e.g. CGM screenshots) never
                # overflow into the sticky note rows below.  Width is auto-calculated by
                # Miro from the image's actual aspect ratio.
                "geometry": {"height": _IMAGE_HEIGHT},
                "parent": {"id": frame_id},
            }
        )

        url = f"{_MIRO_API_BASE}/boards/{self._board_id}/images"
        headers = {"Authorization": f"Bearer {self._access_token}"}

        async with httpx.AsyncClient() as client:
            retry_delays = list(self._retry_delays)
            for attempt in range(len(retry_delays) + 1):
                try:
                    img_filename = f"{image['type']}_{idx}.jpg"
                    response = await client.post(
                        url,
                        headers=headers,
                        data={"data": data_field},
                        files={"resource": (img_filename, image["file_bytes"], "image/jpeg")},
                    )
                except (httpx.RequestError, OSError) as exc:
                    logger.warning(
                        "Image upload network error: telegram_file_id=%s error=%s",
                        image.get("telegram_file_id"),
                        exc,
                    )
                    return None

                if response.status_code == 201:
                    return str(response.json()["id"])

                if response.status_code == 429:
                    if attempt >= len(retry_delays):
                        logger.warning(
                            "Image upload rate-limited (giving up): telegram_file_id=%s",
                            image.get("telegram_file_id"),
                        )
                        return None
                    retry_after = float(response.headers.get("Retry-After", retry_delays[attempt]))
                    await asyncio.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    if attempt >= len(retry_delays):
                        logger.warning(
                            "Image upload server error: telegram_file_id=%s status=%d",
                            image.get("telegram_file_id"),
                            response.status_code,
                        )
                        return None
                    await asyncio.sleep(retry_delays[attempt])
                    continue

                # 400, 413, other 4xx — fail immediately, add placeholder
                logger.warning(
                    "Image upload failed: telegram_file_id=%s status=%d",
                    image.get("telegram_file_id"),
                    response.status_code,
                )
                return None
        return None

    async def _add_sticky_note(
        self,
        frame_id: str,
        content: str,
        style: dict[str, Any],
        position: dict[str, Any],
        geometry: dict[str, Any],
    ) -> str:
        """Create a sticky note inside the frame.

        Returns the sticky note ID. Raises MiroError on unrecoverable failure.
        """
        url = f"{_MIRO_API_BASE}/boards/{self._board_id}/sticky_notes"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload: dict[str, Any] = {
            "data": {"content": content, "shape": "rectangle"},
            "style": style,
            "position": position,
            "geometry": geometry,
            "parent": {"id": frame_id},
        }

        async with httpx.AsyncClient() as client:
            retry_delays = list(self._retry_delays)
            for attempt in range(len(retry_delays) + 1):
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 201:
                    return str(response.json()["id"])
                if response.status_code == 429:
                    if attempt >= len(retry_delays):
                        raise MiroError("Miro rate limit exceeded adding sticky note")
                    retry_after = float(response.headers.get("Retry-After", retry_delays[attempt]))
                    await asyncio.sleep(retry_after)
                    continue
                if response.status_code >= 500:
                    if attempt >= len(retry_delays):
                        raise MiroError(
                            f"Miro server error adding sticky note: {response.status_code}"
                        )
                    await asyncio.sleep(retry_delays[attempt])
                    continue
                raise MiroError(
                    f"Sticky note creation failed {response.status_code}: {response.text[:200]}"
                )
        raise MiroError("Sticky note creation failed — no successful response")

    def _build_section_text(self, analysis: Any, section: str, lang: str = "en") -> str:
        """Build formatted text content for a sticky note section.

        Sections: "food", "activity", "glucose", "correlation", "recommendations".
        Falls back to a generic unavailable message if JSON is None/invalid.
        """
        fallback = "Analysis unavailable for this section — please re-submit your session."

        if section == "food":
            try:
                nutrition = json.loads(analysis.nutrition_json)
                items = nutrition.get("food_items") or []
                items_str = ", ".join(str(i) for i in items) if items else "Unknown"
                carbs = nutrition.get("carbs_g", "?")
                proteins = nutrition.get("proteins_g", "?")
                fats = nutrition.get("fats_g", "?")
                gi_cat = nutrition.get("gi_category") or "?"
                gi_est = nutrition.get("gi_estimate", "?")
                narrative = nutrition.get("glucose_impact_narrative", "")
                lines = [
                    _t("miro_food_header", lang) + "\n",
                    f"• Items: {items_str}",
                    f"• Carbs: {carbs}g | Protein: {proteins}g | Fat: {fats}g",
                    f"• GI: {gi_cat} (~{gi_est})",
                ]
                if narrative:
                    lines.append(f"\n{narrative}")
                return "\n".join(lines)
            except (json.JSONDecodeError, TypeError, AttributeError):
                return fallback

        if section == "activity":
            try:
                activity_hdr = _t("miro_activity_header", lang)
                if not analysis.activity_json:
                    return f"{activity_hdr}\n\nNo activity logged"
                activity = json.loads(analysis.activity_json)
                description = activity.get("description")
                modulation = activity.get("glucose_modulation", "")
                effect = activity.get("effect_summary", "")
                if not description:
                    return f"{activity_hdr}\n\nNo activity logged"
                lines = [activity_hdr + "\n", f"• {description}"]
                if modulation:
                    lines.append(f"• {modulation}")
                if effect:
                    lines.append(f"• {effect}")
                return "\n".join(lines)
            except (json.JSONDecodeError, TypeError, AttributeError):
                return fallback

        if section == "glucose":
            try:
                glucose_curve = json.loads(analysis.glucose_curve_json)
                lines = [_t("miro_glucose_header", lang) + "\n"]
                for point in glucose_curve:
                    label = point.get("timing_label", "?")
                    value = point.get("estimated_value_mg_dl", "?")
                    in_range = point.get("in_range")
                    shape = point.get("curve_shape_label", "")
                    if in_range is True:
                        indicator = "✅ in range"
                    elif in_range is False:
                        indicator = "⚠️ out of range"
                    else:
                        indicator = ""
                    line = f"• {label}: {value} mg/dL — {indicator}"
                    if shape:
                        line += f" | Shape: {shape}"
                    lines.append(line)
                # Check if CGM was unparseable
                try:
                    has_raw = hasattr(analysis, "raw_response")
                    raw = json.loads(analysis.raw_response) if has_raw else {}
                    if not raw.get("cgm_parseable", True):
                        err = raw.get("cgm_parse_error", "unknown")
                        return (
                            f"{_t('miro_glucose_header', lang)}\n\n⚠️ CGM unreadable: {err}. "
                            "Please re-submit a clearer screenshot."
                        )
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass
                return "\n".join(lines)
            except (json.JSONDecodeError, TypeError, AttributeError):
                return fallback

        if section == "correlation":
            try:
                correlation = json.loads(analysis.correlation_json)
                lines = [_t("miro_correlation_header", lang) + "\n"]
                spikes = correlation.get("spikes") or []
                dips = correlation.get("dips") or []
                stable = correlation.get("stable_zones") or []
                summary = correlation.get("summary", "")
                for s in spikes:
                    lines.append(f"• {s}")
                for d in dips:
                    lines.append(f"• {d}")
                for z in stable:
                    lines.append(f"• {z}")
                if summary:
                    lines.append(f"\n{summary}")
                return "\n".join(lines)
            except (json.JSONDecodeError, TypeError, AttributeError):
                return fallback

        if section == "recommendations":
            try:
                recommendations = json.loads(analysis.recommendations_json)
                rec_hdr = _t("miro_recommendations_header", lang)
                if not recommendations:
                    return (
                        f"{rec_hdr}\n\n" "No specific recommendations generated for this session."
                    )
                sorted_recs = sorted(recommendations, key=lambda r: r.get("priority", 99))
                lines = [rec_hdr + "\n"]
                for rec in sorted_recs:
                    lines.append(f"• {rec.get('text', '')}")
                return "\n".join(lines)
            except (json.JSONDecodeError, TypeError, AttributeError):
                return fallback

        return fallback

    async def create_enhanced_session_card(
        self,
        analysis: Any,
        session_images: list[dict[str, Any]],
        lang: str = "en",
    ) -> str:
        """Create an enhanced Miro Frame card with embedded photos and rich analysis sections.

        Steps:
        1. Create Frame container
        2. Upload food photos (first) then CGM screenshots as Image items (FR-002)
           — on failure: add placeholder sticky note (FR-011)
        3. Add separator + 5 analysis sections as Sticky Notes

        Returns: frame ID
        Raises: MiroError if frame creation fails (images/sections fail gracefully)
        """
        anon_id = self._anonymise_user_id(analysis.user_id)
        try:
            timestamp = analysis.created_at.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            timestamp = "unknown time"

        title = f"GlucoTrack Session — {timestamp} [User #{anon_id}]"
        n_images = len(session_images)

        # Step 1: Create frame (raises MiroError on failure)
        frame_id = await self._create_frame(
            title=title, user_id=analysis.user_id, n_images=n_images
        )
        logger.info("Created Miro frame %s for analysis %s", frame_id, analysis.id)

        # When an item has parent.id, Miro treats position x,y as frame-relative
        # (measured from the frame's top-left corner with origin: center for the item),
        # matching the same convention used by the multipart image upload endpoint.
        # FixedRatioNoRotationGeometry accepts EITHER width OR height, not both.
        n_image_rows = math.ceil(n_images / _IMAGES_PER_ROW) if n_images > 0 else 0

        # Step 2: Upload images (food first, then CGM)
        food_images = [img for img in session_images if img.get("type") == "food"]
        cgm_images = [img for img in session_images if img.get("type") == "cgm"]
        ordered_images = food_images + cgm_images

        for idx, image in enumerate(ordered_images):
            img_id = await self._upload_image(frame_id=frame_id, image=image, idx=idx)
            if img_id is None:
                # FR-011: placeholder sticky note at the image's frame-relative position
                col = idx % _IMAGES_PER_ROW
                row = idx // _IMAGES_PER_ROW
                x_center = _IMAGE_X_STEP * col + 20 + _IMAGE_WIDTH // 2
                y_center = _IMAGE_Y_START + row * _IMAGE_ROW_HEIGHT + _IMAGE_HEIGHT // 2
                try:
                    await self._add_sticky_note(
                        frame_id=frame_id,
                        content="⚠️ Image unavailable\n(upload failed)",
                        style=_STYLE_PLACEHOLDER,
                        position={"x": x_center, "y": y_center},
                        geometry={"width": _IMAGE_WIDTH},
                    )
                except MiroError as exc:
                    logger.warning("Failed to add image placeholder: %s", exc)

        # Step 3: Add 5 analysis sections + header in a 2-column × 3-row grid
        # Layout: food | glucose  /  recommendations | correlation  /  activity | header
        section_y_start = _IMAGE_Y_START + n_image_rows * _IMAGE_ROW_HEIGHT + _SECTION_TOP_MARGIN
        col_centers = [
            _FRAME_WIDTH * (2 * c + 1) // (2 * _SECTION_COLS) for c in range(_SECTION_COLS)
        ]  # [300, 900] for a 1200px frame split into 2 columns

        section_grid = [
            # (section_name_or_sentinel, row, col)
            ("food", 0, 0),
            ("glucose", 0, 1),
            ("recommendations", 1, 0),
            ("correlation", 1, 1),
            ("activity", 2, 0),
            ("_header", 2, 1),  # analysis header / separator note
        ]

        for section_name, row, col in section_grid:
            x = col_centers[col]
            y = section_y_start + row * (_SECTION_HEIGHT + _SECTION_GAP)
            if section_name == "_header":
                content = "─── Analysis ───────────────────────"
                style = _STYLE_SEPARATOR
            else:
                try:
                    content = self._build_section_text(analysis, section_name, lang=lang)
                except Exception:
                    content = (
                        "Analysis unavailable for this section" " — please re-submit your session."
                    )
                style = _STYLE_SECTION
            try:
                await self._add_sticky_note(
                    frame_id=frame_id,
                    content=content,
                    style=style,
                    position={"x": x, "y": y},
                    geometry={"width": _SECTION_WIDTH},
                )
            except MiroError as exc:
                logger.warning("Failed to add section '%s': %s", section_name, exc)

        logger.info("Enhanced Miro card complete: frame=%s analysis=%s", frame_id, analysis.id)
        return frame_id
