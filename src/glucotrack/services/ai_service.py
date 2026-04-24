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
from collections.abc import Callable
from datetime import date
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

_LANGUAGE_INSTRUCTIONS: dict[str, str] = {
    "ru": (
        "Respond entirely in Russian. All narrative text, section explanations, "
        "recommendations, and notes must be in Russian. "
        "Numeric values, units (mg/dL), and JSON keys must remain unchanged."
    ),
}

SESSION_ANALYSIS_SYSTEM_PROMPT = """You are a glucose analysis AI for GlucoTrack. \
Analyse the provided food photos and CGM screenshots and return a JSON object with \
exactly this structure (no markdown, pure JSON):

{
  "nutrition": {
    "carbs_g": <number or null>,
    "proteins_g": <number or null>,
    "fats_g": <number or null>,
    "gi_estimate": <number 0-100 or null>,
    "gi_category": "<'low' | 'medium' | 'high' | null: GI category based on gi_estimate>",
    "food_items": ["<identified food item 1>", "<food item 2>"],
    "glucose_impact_narrative": "<2-3 sentences explaining expected glucose impact, \
must explicitly reference the 70-140 mg/dL target range>",
    "notes": "<string>"
  },
  "activity": {
    "description": "<string: what activity was logged, or null if none>",
    "glucose_modulation": "<string: how this activity affects glucose response; \
use 'No activity logged.' when description is null>",
    "effect_summary": "<string: overall effect observed or expected; \
use 'No activity to analyse.' when description is null>"
  },
  "glucose_curve": [
    {
      "timing_label": "<string>",
      "estimated_value_mg_dl": <number or null>,
      "in_range": <boolean: true if value is 70-140 mg/dL, else false, null if unknown>,
      "notes": "<string>",
      "curve_shape_label": "<descriptive label e.g. 'sharp spike with recovery', \
'stable within range', 'gradual rise', 'gradual rise with plateau'>"
    }
  ],
  "correlation": {
    "spikes": ["<cause-effect statement explicitly naming food or activity>"],
    "dips": ["<cause-effect statement>"],
    "stable_zones": ["<explanation>"],
    "summary": "<2+ sentences with explicit references to foods or activities from this session>"
  },
  "recommendations": [
    {
      "priority": <1-5 integer>,
      "text": "<session-specific actionable suggestion referencing the meal or activity by name>"
    }
  ],
  "target_range_note": "<string: summary of 70-140 mg/dL compliance>",
  "cgm_parseable": <boolean: true if you could read the CGM screenshot>,
  "cgm_parse_error": "<string: reason if cgm_parseable is false, else null>",
  "executive_summary": "<2-3 sentences: food consumed, glucose response, key insight>",
  "encouragement": "<1 sentence of positive feedback or encouragement for the user>"
}

The healthy glucose target range is 70–140 mg/dL. Explicitly note any readings \
outside this range. If the CGM screenshot is unreadable, set cgm_parseable=false. \
gi_category MUST be 'low' (GI < 55), 'medium' (GI 55-69), 'high' (GI >= 70), or null. \
When no activity was logged, set activity.description to null."""


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _detect_media_type(data: bytes) -> str:
    """Return MIME type for image bytes based on magic header."""
    if data[:8] == _PNG_MAGIC:
        return "image/png"
    return "image/jpeg"


def _extract_json(text: str) -> str:
    """Extract the JSON object from a Claude response.

    Claude may wrap the JSON in markdown code fences (```json...``` or ```...```)
    or prefix it with prose.  We try three strategies in order:

    1. Direct parse (fast-path: response is already clean JSON).
    2. Strip a markdown code fence and return the inner content.
    3. Find the first ``{`` … last ``}`` substring (handles preamble text).

    Returns the best candidate string so the caller can attempt json.loads().
    If none of the heuristics produce a valid JSON string the original text is
    returned so the caller's JSONDecodeError reports the full raw content.
    """
    stripped = text.strip()

    # Fast-path: already valid JSON
    try:
        json.loads(stripped)
        return stripped
    except json.JSONDecodeError:
        pass

    # Strip ```json ... ``` or ``` ... ``` fences
    if stripped.startswith("```"):
        # Remove the opening fence line (```json or ```)
        lines = stripped.splitlines()
        # Drop first and last lines if they are fence markers
        inner_lines = lines[1:]
        if inner_lines and inner_lines[-1].strip() == "```":
            inner_lines = inner_lines[:-1]
        candidate = "\n".join(inner_lines).strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # Find first { … last } in the text (handles leading prose)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        candidate = stripped[start : end + 1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # Give up — return original so the caller logs the full raw text
    return text


class AnalysisError(Exception):
    """Raised when Claude API call fails after retries."""


class RateLimitExceeded(Exception):  # noqa: N818
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
        food_entries: list[dict[str, Any]],
        cgm_entries: list[dict[str, Any]],
        activity_entries: list[dict[str, Any]],
        load_file_bytes: Callable,  # type: ignore[type-arg]
        language: str = "en",
    ) -> dict[str, Any]:
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
        content: list[dict[str, Any]] = []

        # Text context block
        activity_text = "; ".join(e.get("description", "") for e in activity_entries)
        cgm_labels = ", ".join(e.get("timing_label", "?") for e in cgm_entries)
        context_text = "Session context:"
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
                    "source": {
                        "type": "base64",
                        "media_type": _detect_media_type(image_bytes),
                        "data": b64,
                    },
                }
            )

        # CGM screenshot blocks
        for entry in cgm_entries:
            image_bytes = await load_file_bytes(entry["telegram_file_id"])
            b64 = base64.standard_b64encode(image_bytes).decode()
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": _detect_media_type(image_bytes),
                        "data": b64,
                    },
                }
            )

        system = SESSION_ANALYSIS_SYSTEM_PROMPT
        lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, "")
        if lang_instruction:
            system = system + "\n\n" + lang_instruction

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],  # type: ignore[typeddict-item]
            )
            self._increment_call_count(user_id)
        except anthropic.APIStatusError as exc:
            logger.error("Claude API error (user_id=%d): %s", user_id, exc)
            raise AnalysisError(f"Claude API error: {exc}") from exc

        first_block = response.content[0]
        raw_text: str = getattr(first_block, "text", "")  # TextBlock has .text; others do not
        try:
            result: dict[str, Any] = json.loads(_extract_json(raw_text))
            return result
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Claude response as JSON: %s", raw_text[:200])
            raise AnalysisError("Claude response was not valid JSON.") from exc
