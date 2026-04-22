"""Mock implementations for sandbox testing without real API credentials.

Each mock mirrors the public interface of its real counterpart but returns
pre-baked, realistic responses with simulated network latency.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Realistic pre-baked analysis response — mirrors what Claude returns
MOCK_ANALYSIS_RESPONSE: dict[str, Any] = {
    "nutrition": {
        "carbs_g": 65,
        "proteins_g": 28,
        "fats_g": 12,
        "gi_estimate": 58,
        "notes": "Mixed plate — steamed rice, grilled chicken breast, broccoli with olive oil",
    },
    "glucose_curve": [
        {
            "timing_label": "fasting",
            "estimated_value_mg_dl": 92,
            "in_range": True,
            "notes": "Normal fasting level, well within 70–140 range",
        },
        {
            "timing_label": "1h_post_meal",
            "estimated_value_mg_dl": 148,
            "in_range": False,
            "notes": "Moderate post-meal spike, 8 mg/dL above upper threshold",
        },
        {
            "timing_label": "2h_post_meal",
            "estimated_value_mg_dl": 118,
            "in_range": True,
            "notes": "Returning to normal range — good recovery trajectory",
        },
    ],
    "correlation": {
        "spikes": ["1h post-meal: 148 mg/dL (above 140 mg/dL threshold)"],
        "dips": [],
        "stable_zones": ["Fasting: 92 mg/dL", "2h post-meal: 118 mg/dL"],
        "summary": (
            "Moderate post-meal glucose spike likely driven by the rice portion (high GI). "
            "Spike resolves within 2 hours. Pre-meal walk helped limit peak height."
        ),
    },
    "recommendations": [
        {
            "priority": 1,
            "text": (
                "Try a 'food order hack': eat vegetables first, then protein, then carbs. "
                "This sequence reduces post-meal spikes by 20–30% in studies."
            ),
        },
        {
            "priority": 2,
            "text": (
                "A 20–30 min walk within 30 minutes after eating can flatten the "
                "glucose curve. Your pre-meal walk already helped — try post-meal too."
            ),
        },
    ],
    "target_range_note": (
        "1 of 3 readings (33%) outside 70–140 mg/dL target range. "
        "The brief spike at 1h is manageable; 2h reading shows good recovery."
    ),
    "cgm_parseable": True,
    "cgm_parse_error": None,
}


class MockAIService:
    """Returns pre-baked analysis without calling the Anthropic API.

    Simulates ~500ms API latency by default so the UI shows realistic timing.
    """

    def __init__(self, latency_seconds: float = 0.5) -> None:
        self._latency = latency_seconds

    async def analyse_session(
        self,
        user_id: int,
        food_entries: list[dict[str, Any]],
        cgm_entries: list[dict[str, Any]],
        activity_entries: list[dict[str, Any]],
        load_file_bytes: Any,
    ) -> dict[str, Any]:
        """Return pre-baked analysis response after simulated latency."""
        await asyncio.sleep(self._latency)
        logger.debug(
            "MockAIService: returning pre-baked response for user_id=%d "
            "(food=%d, cgm=%d, activity=%d)",
            user_id,
            len(food_entries),
            len(cgm_entries),
            len(activity_entries),
        )
        return dict(MOCK_ANALYSIS_RESPONSE)


class MockMiroService:
    """Returns a fake Miro card ID without calling the Miro REST API.

    The public ``board_id`` attribute mirrors the real MiroService interface.
    """

    def __init__(self, latency_seconds: float = 0.3) -> None:
        self._latency = latency_seconds
        self.board_id = "mock_board_SANDBOX123"

    async def create_session_card(self, analysis: Any) -> str:
        """Return a fake card ID after simulated latency."""
        await asyncio.sleep(self._latency)
        logger.debug("MockMiroService: returning mock card id for analysis=%s", analysis.id)
        return "mock_card_XYZ789"


class MockTelegramBot:
    """Captures Telegram messages instead of sending them to the real API.

    Used in sandbox runs to collect bot output for display in the event log.
    """

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
    ) -> None:
        self.sent_messages.append({"chat_id": chat_id, "text": text, "parse_mode": parse_mode})
        logger.debug("MockTelegramBot: captured message to chat_id=%d", chat_id)
