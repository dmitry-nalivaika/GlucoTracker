"""MiroService — Miro REST API integration.

Isolated per Constitution III: "storage behind StorageRepository;
input channels behind adapter." Miro is an output channel.

FR-009: Miro failure MUST NOT block Telegram delivery.
Contract: contracts/miro-api-schema.md
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_MIRO_API_BASE = "https://api.miro.com/v2"
# Default exponential backoff delays (seconds) for 5xx retries
_DEFAULT_RETRY_DELAYS: tuple[float, ...] = (1.0, 2.0, 4.0)


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
            "style": {"fillColor": "#d5f5e3"},
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
