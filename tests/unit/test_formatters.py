"""Unit tests for formatters.py — T050.

All formatter functions must return valid MarkdownV2 content without
raw stack traces or Python exceptions exposed to users.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from glucotrack.bot import formatters


def _make_analysis(
    carbs: int = 50,
    proteins: int = 25,
    fats: int = 12,
    gi: int = 70,
    notes: str = "",
    activity_json: str | None = None,
) -> MagicMock:
    analysis = MagicMock()
    analysis.nutrition_json = json.dumps(
        {
            "carbs_g": carbs,
            "proteins_g": proteins,
            "fats_g": fats,
            "gi_estimate": gi,
            "notes": notes,
        }
    )
    analysis.glucose_curve_json = json.dumps(
        [
            {"timing_label": "before", "estimated_value_mg_dl": 90, "in_range": True, "notes": ""},
            {
                "timing_label": "1h after",
                "estimated_value_mg_dl": 155,
                "in_range": False,
                "notes": "spike",
            },
        ]
    )
    analysis.correlation_json = json.dumps(
        {
            "spikes": ["1h after"],
            "dips": [],
            "stable_zones": [],
            "summary": "Glucose spiked after meal.",
        }
    )
    analysis.recommendations_json = json.dumps(
        [
            {"priority": 1, "text": "Reduce refined carbs."},
            {"priority": 2, "text": "Walk 10 minutes after eating."},
        ]
    )
    analysis.within_target_notes = "One reading above 140 mg/dL."
    analysis.activity_json = activity_json
    return analysis


class TestFormatters:
    """All formatter functions return valid MarkdownV2 content."""

    def test_fmt_analysis_result_contains_all_four_sections(self) -> None:
        text = formatters.fmt_analysis_result(_make_analysis())
        assert "Nutrition" in text
        assert "Glucose" in text
        assert "Correlation" in text
        assert "Recommendations" in text

    def test_fmt_analysis_result_contains_macro_values(self) -> None:
        text = formatters.fmt_analysis_result(_make_analysis(carbs=80, proteins=30, fats=15, gi=75))
        assert "80" in text
        assert "30" in text
        assert "15" in text
        assert "75" in text

    def test_fmt_analysis_result_shows_range_indicators(self) -> None:
        text = formatters.fmt_analysis_result(_make_analysis())
        # in_range=True → ✅, in_range=False → ⚠️
        assert "✅" in text
        assert "⚠️" in text

    def test_fmt_analysis_result_includes_target_note(self) -> None:
        analysis = _make_analysis()
        analysis.within_target_notes = "One spike above 140."
        text = formatters.fmt_analysis_result(analysis)
        assert "140" in text

    def test_fmt_analysis_result_no_stack_trace(self) -> None:
        text = formatters.fmt_analysis_result(_make_analysis())
        assert "Traceback" not in text
        assert "Exception" not in text
        assert "Error" not in text

    def test_fmt_analysis_error_is_human_readable(self) -> None:
        text = formatters.fmt_analysis_error()
        assert "Analysis failed" in text
        assert "Traceback" not in text
        assert len(text) > 10

    def test_fmt_cgm_unparseable_is_human_readable(self) -> None:
        text = formatters.fmt_cgm_unparseable()
        assert "screenshot" in text.lower() or "cgm" in text.lower()
        assert "Traceback" not in text

    def test_fmt_generic_error_is_human_readable(self) -> None:
        text = formatters.fmt_generic_error()
        assert "wrong" in text.lower() or "error" in text.lower()
        assert "Traceback" not in text

    def test_fmt_trend_insufficient_includes_counts(self) -> None:
        text = formatters.fmt_trend_insufficient(current=2, required=5)
        assert "2" in text
        assert "5" in text

    def test_fmt_trend_coming_soon_includes_count(self) -> None:
        text = formatters.fmt_trend_coming_soon(7)
        assert "7" in text

    def test_fmt_welcome_returns_non_empty_string(self) -> None:
        text = formatters.fmt_welcome("Alice")
        assert "Alice" in text
        assert len(text) > 20

    def test_fmt_help_contains_all_commands(self) -> None:
        text = formatters.fmt_help()
        for cmd in ["/start", "/new", "/done", "/status", "/trend", "/cancel", "/help"]:
            assert cmd in text

    def test_fmt_session_status_includes_counts(self) -> None:
        text = formatters.fmt_session_status(food=3, cgm=2, activity=1)
        assert "3" in text
        assert "2" in text
        assert "1" in text

    # ── Activity section tests (T011, feature 002) ───────────────────────────

    def test_fmt_analysis_result_shows_activity_section_when_present(self) -> None:
        """Activity section appears when activity_json is set (FR-010)."""
        activity = json.dumps(
            {
                "description": "30-min brisk walk",
                "glucose_modulation": "reduced post-meal spike",
                "effect_summary": "moderate lowering effect",
            }
        )
        text = formatters.fmt_analysis_result(_make_analysis(activity_json=activity))
        assert "Activity" in text
        assert "30-min brisk walk" in text or "walk" in text.lower()

    def test_fmt_analysis_result_omits_activity_section_when_none(self) -> None:
        """Activity section is absent when activity_json is None (backward compat)."""
        text = formatters.fmt_analysis_result(_make_analysis(activity_json=None))
        # Should not raise; must still contain the four original sections
        assert "Nutrition" in text
        assert "Glucose" in text
        assert "Correlation" in text
        assert "Recommendations" in text

    # ── Guided flow formatters (feature 004, T006) ───────────────────────────

    def test_fmt_food_ack_guided_en(self) -> None:
        """Food ack with guided=True includes a next-step hint in English."""
        text = formatters.fmt_food_ack(guided=True)
        assert "CGM" in text or "cgm" in text.lower() or "/done" in text

    def test_fmt_food_ack_guided_ru(self) -> None:
        """Food ack with guided=True includes a next-step hint in Russian."""
        text = formatters.fmt_food_ack(lang="ru", guided=True)
        assert "CGM" in text or "/done" in text

    def test_fmt_cgm_ack_guided_en(self) -> None:
        """CGM ack with guided=True includes a next-step hint in English."""
        text = formatters.fmt_cgm_ack("1 hour after", guided=True)
        assert "/done" in text or "activity" in text.lower()

    def test_fmt_activity_ack_guided_en(self) -> None:
        """Activity ack with guided=True includes a next-step hint in English."""
        text = formatters.fmt_activity_ack("walked 20 min", guided=True)
        assert "/done" in text

    def test_fmt_session_start_prompt_en(self) -> None:
        """Session start prompt tells user to send a food photo."""
        text = formatters.fmt_session_start_prompt()
        assert "photo" in text.lower() or "food" in text.lower()

    def test_fmt_session_start_prompt_ru(self) -> None:
        """Session start prompt is in Russian when lang=ru."""
        text = formatters.fmt_session_start_prompt(lang="ru")
        # Should contain at least one Cyrillic character
        assert any("\u0400" <= c <= "\u04ff" for c in text)

    def test_fmt_food_ack_without_guided_unchanged(self) -> None:
        """fmt_food_ack without guided= flag behaves as before (backward compat)."""
        text = formatters.fmt_food_ack()
        assert "saved" in text.lower() or "сохранено" in text.lower() or "✅" in text

    def test_fmt_analysis_result_no_activity_logged_message(self) -> None:
        """When activity has null description, show 'No activity' message."""
        activity = json.dumps(
            {
                "description": None,
                "glucose_modulation": "No activity logged.",
                "effect_summary": "No activity to analyse.",
            }
        )
        text = formatters.fmt_analysis_result(_make_analysis(activity_json=activity))
        assert "Activity" in text
        assert "No activity" in text
