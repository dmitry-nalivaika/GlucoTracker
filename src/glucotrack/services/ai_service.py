"""AIService — Claude API integration.

Isolated per Constitution III: "The Claude API integration MUST be isolated
in a dedicated AI service module; domain code MUST NOT call Claude directly."

Rate limiting and token budgeting enforce Constitution VII cost guard.
"""
from __future__ import annotations

import base64
import json
import logging
from collections import defaultdict
from datetime import date
from typing import Callable

import anthropic

logger = logging.getLogger(__name__)

SESSION_ANALYSIS_SYSTEM_PROMPT = """You are a glucose analysis AI for GlucoTrack. \
Analyse the provided food photos and CGM screenshots and return a JSON object with \
exactly this structure (no markdown, pure JSON):

{
  "nutrition": {
    "carbs_g": <number or null>,
    "proteins_g": <number or null>,
    "fats_g": <number or null>,
    "gi_estimate": <number 0-100 or null>,
    "notes": "<string>"
  },
  "glucose_curve": [
    {
      "timing_label": "<string>",
      "estimated_value_mg_dl": <number or null>,
      "in_range": <boolean: true if value is 70-140 mg/dL, else false, null if unknown>,
      "notes": "<string>"
    }
  ],
  "correlation": {
    "spikes": ["<string>"],
    "dips": ["<string>"],
    "stable_zones": ["<string>"],
    "summary": "<string>"
  },
  "recommendations": [
    {
      "priority": <1-5 integer>,
      "text": "<actionable recommendation>"
    }
  ],
  "target_range_note": "<string: summary of 70-140 mg/dL compliance>",
  "cgm_parseable": <boolean: true if you could read the CGM screenshot>,
  "cgm_parse_error": "<string: reason if cgm_parseable is false, else null>"
}

The healthy glucose target range is 70–140 mg/dL. Explicitly note any readings \
outside this range. If the CGM screenshot is unreadable, set cgm_parseable=false."""


class AnalysisError(Exception):
    """Raised when Claude API call fails after retries."""


class RateLimitExceeded(Exception):
    """Raised when a user exceeds their daily AI analysis call limit (Constitution VII)."""

    def __init__(self, user_id: int, limit: int) -> None:
        self.user_id = user_id
        self.limit = limit
        super().__init__(f"User {user_id} exceeded daily limit of {limit} analysis calls.")


class AIService:
    """Wraps the Anthropic SDK for session and trend analysis.

    Rate limiting: in-memory token bucket per user_id, keyed by date.
    For multi-instance deployments, replace with Redis-backed rate limiting.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        max_calls_per_user_per_day: int,
        max_tokens_per_session: int,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_calls = max_calls_per_user_per_day
        self._max_tokens = max_tokens_per_session
        # {(user_id, date): call_count}
        self._call_counts: dict[tuple[int, date], int] = defaultdict(int)

    def _check_rate_limit(self, user_id: int) -> None:
        """Raise RateLimitExceeded if user has exceeded daily limit."""
        today = date.today()
        key = (user_id, today)
        if self._call_counts[key] >= self._max_calls:
            raise RateLimitExceeded(user_id, self._max_calls)

    def _increment_call_count(self, user_id: int) -> None:
        today = date.today()
        self._call_counts[(user_id, today)] += 1

    async def analyse_session(
        self,
        user_id: int,
        food_entries: list[dict],
        cgm_entries: list[dict],
        activity_entries: list[dict],
        load_file_bytes: Callable,
    ) -> dict:
        """Analyse a session using Claude vision API.

        Args:
            user_id: Session owner (for rate limiting).
            food_entries: List of dicts with 'telegram_file_id' and 'file_path'.
            cgm_entries: List of dicts with 'telegram_file_id', 'timing_label', 'file_path'.
            activity_entries: List of dicts with 'description'.
            load_file_bytes: Async callable(telegram_file_id) -> bytes.

        Returns:
            Parsed JSON response dict.

        Raises:
            RateLimitExceeded: If user exceeds daily limit.
            AnalysisError: If Claude API call fails after retry.
        """
        self._check_rate_limit(user_id)

        # Build content blocks
        content: list[dict] = []

        # Text context block
        activity_text = "; ".join(e.get("description", "") for e in activity_entries)
        cgm_labels = ", ".join(e.get("timing_label", "?") for e in cgm_entries)
        context_text = f"Session context:"
        if activity_text:
            context_text += f" Activity: {activity_text}."
        if cgm_labels:
            context_text += f" CGM timing labels: {cgm_labels}."
        content.append({"type": "text", "text": context_text})

        # Food photo blocks
        for entry in food_entries:
            image_bytes = await load_file_bytes(entry["telegram_file_id"])
            b64 = base64.standard_b64encode(image_bytes).decode()
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                }
            )

        # CGM screenshot blocks
        for entry in cgm_entries:
            image_bytes = await load_file_bytes(entry["telegram_file_id"])
            b64 = base64.standard_b64encode(image_bytes).decode()
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                }
            )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=SESSION_ANALYSIS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            self._increment_call_count(user_id)
        except anthropic.APIStatusError as exc:
            logger.error("Claude API error (user_id=%d): %s", user_id, exc)
            raise AnalysisError(f"Claude API error: {exc}") from exc

        raw_text = response.content[0].text
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Claude response as JSON: %s", raw_text[:200])
            raise AnalysisError("Claude response was not valid JSON.") from exc
