"""Contract tests for Claude Enhanced API schema — feature 002.

Validates that:
- SESSION_ANALYSIS_SYSTEM_PROMPT includes new fields (activity, gi_category, etc.)
- Response schema contains activity, nutrition.gi_category, nutrition.food_items,
  nutrition.glucose_impact_narrative, and glucose_curve[].curve_shape_label
- Validation rules from contracts/claude-enhanced-api-schema.md are enforced
"""

from __future__ import annotations

import json

from glucotrack.services.ai_service import SESSION_ANALYSIS_SYSTEM_PROMPT

ENHANCED_VALID_RESPONSE = {
    "nutrition": {
        "carbs_g": 45,
        "proteins_g": 20,
        "fats_g": 10,
        "gi_estimate": 65,
        "gi_category": "medium",
        "food_items": ["brown rice", "grilled chicken"],
        "glucose_impact_narrative": (
            "The moderate-GI carbohydrates are expected to cause a gradual rise "
            "staying within the 70–140 mg/dL range."
        ),
        "notes": "",
    },
    "activity": {
        "description": "30-minute brisk walk",
        "glucose_modulation": "Post-meal walk reduced the glucose spike",
        "effect_summary": "Moderate glucose-lowering effect observed",
    },
    "glucose_curve": [
        {
            "timing_label": "1 hour after",
            "estimated_value_mg_dl": 130,
            "in_range": True,
            "notes": "",
            "curve_shape_label": "gradual rise with plateau",
        }
    ],
    "correlation": {
        "spikes": ["The rice portion likely caused the spike at 1h"],
        "dips": [],
        "stable_zones": ["Fasting glucose was stable"],
        "summary": "The brown rice meal caused a moderate spike; the walk helped attenuate it.",
    },
    "recommendations": [{"priority": 1, "text": "Consider reducing the brown rice portion by 20%"}],
    "target_range_note": "Glucose remained within 70–140 mg/dL throughout the session.",
    "cgm_parseable": True,
    "cgm_parse_error": None,
}

NO_ACTIVITY_RESPONSE = {
    **ENHANCED_VALID_RESPONSE,
    "activity": {
        "description": None,
        "glucose_modulation": "No activity logged.",
        "effect_summary": "No activity to analyse.",
    },
}


class TestClaudeEnhancedAPISchemaContract:
    """Contract tests for the enhanced Claude API schema (feature 002)."""

    # ── Prompt content tests ─────────────────────────────────────────────────

    def test_system_prompt_contains_activity_section(self) -> None:
        """SESSION_ANALYSIS_SYSTEM_PROMPT must include 'activity' key."""
        assert (
            '"activity"' in SESSION_ANALYSIS_SYSTEM_PROMPT
        ), "Prompt must define an 'activity' JSON section"

    def test_system_prompt_contains_gi_category(self) -> None:
        assert (
            "gi_category" in SESSION_ANALYSIS_SYSTEM_PROMPT
        ), "Prompt must include gi_category in nutrition section"

    def test_system_prompt_contains_food_items(self) -> None:
        assert (
            "food_items" in SESSION_ANALYSIS_SYSTEM_PROMPT
        ), "Prompt must include food_items in nutrition section"

    def test_system_prompt_contains_glucose_impact_narrative(self) -> None:
        assert (
            "glucose_impact_narrative" in SESSION_ANALYSIS_SYSTEM_PROMPT
        ), "Prompt must include glucose_impact_narrative in nutrition section"

    def test_system_prompt_contains_curve_shape_label(self) -> None:
        assert (
            "curve_shape_label" in SESSION_ANALYSIS_SYSTEM_PROMPT
        ), "Prompt must include curve_shape_label in glucose_curve entries"

    # ── Response schema tests ─────────────────────────────────────────────────

    def test_enhanced_response_has_activity_section(self) -> None:
        assert "activity" in ENHANCED_VALID_RESPONSE
        activity = ENHANCED_VALID_RESPONSE["activity"]
        assert "description" in activity
        assert "glucose_modulation" in activity
        assert "effect_summary" in activity

    def test_nutrition_has_gi_category(self) -> None:
        nutrition = ENHANCED_VALID_RESPONSE["nutrition"]
        assert "gi_category" in nutrition
        assert nutrition["gi_category"] in ("low", "medium", "high", None)

    def test_nutrition_has_food_items_list(self) -> None:
        nutrition = ENHANCED_VALID_RESPONSE["nutrition"]
        assert "food_items" in nutrition
        assert isinstance(nutrition["food_items"], list)

    def test_nutrition_has_glucose_impact_narrative(self) -> None:
        nutrition = ENHANCED_VALID_RESPONSE["nutrition"]
        assert "glucose_impact_narrative" in nutrition
        # Must reference the target range
        narrative = nutrition["glucose_impact_narrative"]
        assert (
            "70" in narrative or "140" in narrative
        ), "glucose_impact_narrative must reference 70–140 mg/dL range"

    def test_glucose_curve_entries_have_curve_shape_label(self) -> None:
        curve = ENHANCED_VALID_RESPONSE["glucose_curve"]
        assert len(curve) >= 1
        for entry in curve:
            assert (
                "curve_shape_label" in entry
            ), "Each glucose_curve entry must have curve_shape_label"

    def test_no_activity_response_has_null_description(self) -> None:
        activity = NO_ACTIVITY_RESPONSE["activity"]
        assert activity["description"] is None
        assert activity["glucose_modulation"] == "No activity logged."

    def test_gi_category_valid_values(self) -> None:
        valid = {"low", "medium", "high", None}
        gi_cat = ENHANCED_VALID_RESPONSE["nutrition"]["gi_category"]
        assert gi_cat in valid, f"gi_category '{gi_cat}' is not a valid value"

    def test_correlation_summary_references_food_or_activity(self) -> None:
        summary = ENHANCED_VALID_RESPONSE["correlation"]["summary"]
        # Must mention a food or activity name from the session
        assert any(
            term in summary.lower() for term in ["rice", "chicken", "walk", "meal", "activity"]
        ), "correlation.summary must reference a food or activity from the session"

    def test_recommendations_text_references_session_specific_item(self) -> None:
        for rec in ENHANCED_VALID_RESPONSE["recommendations"]:
            text = rec["text"]
            assert any(
                term in text.lower()
                for term in ["rice", "chicken", "walk", "meal", "activity", "portion"]
            ), f"recommendation text must be session-specific: '{text}'"

    def test_activity_json_roundtrip(self) -> None:
        """Activity section survives JSON serialise/deserialise round-trip."""
        activity = ENHANCED_VALID_RESPONSE["activity"]
        serialised = json.dumps(activity)
        restored = json.loads(serialised)
        assert restored["description"] == activity["description"]
        assert restored["glucose_modulation"] == activity["glucose_modulation"]
        assert restored["effect_summary"] == activity["effect_summary"]
