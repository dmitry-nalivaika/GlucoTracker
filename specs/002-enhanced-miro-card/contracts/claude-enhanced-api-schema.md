# Contract: Claude API Enhanced Schema

**Feature**: 002-enhanced-miro-card | **Date**: 2026-04-23
**API**: Anthropic Messages API | **Model**: claude-3-5-sonnet-20241022

This contract REPLACES `specs/001-telegram-mvp-session-logging/contracts/claude-api-schema.md` for all new session analysis calls.

---

## System Prompt (enhanced)

The system prompt is stored in `AIService.SESSION_ANALYSIS_SYSTEM_PROMPT`. The enhanced version
extends the required JSON schema with:
1. An `activity` section (new)
2. `gi_category` and `food_items` and `glucose_impact_narrative` in `nutrition` (new)
3. `curve_shape_label` per glucose reading (new)

---

## Request Body

```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 4000,
  "system": "{SESSION_ANALYSIS_SYSTEM_PROMPT}",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Session context: Activity: {activity_descriptions}. CGM timing labels: {timing_labels}."
        },
        {
          "type": "image",
          "source": { "type": "base64", "media_type": "image/jpeg", "data": "{food_photo_1_b64}" }
        },
        {
          "type": "image",
          "source": { "type": "base64", "media_type": "image/jpeg", "data": "{cgm_screenshot_1_b64}" }
        }
      ]
    }
  ]
}
```

---

## Required Response Schema (pure JSON, no markdown)

```json
{
  "nutrition": {
    "carbs_g": "<number or null>",
    "proteins_g": "<number or null>",
    "fats_g": "<number or null>",
    "gi_estimate": "<number 0-100 or null>",
    "gi_category": "<'low' | 'medium' | 'high' | null>",
    "food_items": ["<identified food item 1>", "<food item 2>"],
    "glucose_impact_narrative": "<2-3 sentences explaining expected glucose impact referencing 70-140 mg/dL>",
    "notes": "<string>"
  },
  "activity": {
    "description": "<string: what activity was logged, or null if none>",
    "glucose_modulation": "<string: how this activity affects glucose response>",
    "effect_summary": "<string: overall effect observed or expected>"
  },
  "glucose_curve": [
    {
      "timing_label": "<string>",
      "estimated_value_mg_dl": "<number or null>",
      "in_range": "<boolean: true if 70-140 mg/dL, else false, null if unknown>",
      "notes": "<string>",
      "curve_shape_label": "<descriptive label: e.g. 'sharp spike with recovery', 'stable within range', 'gradual rise'>"
    }
  ],
  "correlation": {
    "spikes": ["<cause-effect statement: 'The high-carb portion likely caused the spike at 1h'>"],
    "dips": ["<cause-effect statement>"],
    "stable_zones": ["<explanation>"],
    "summary": "<string: 2+ sentences with explicit food/activity references>"
  },
  "recommendations": [
    {
      "priority": "<1-5 integer>",
      "text": "<session-specific actionable suggestion referencing meal or activity by name>"
    }
  ],
  "target_range_note": "<string: summary of 70-140 mg/dL compliance>",
  "cgm_parseable": "<boolean>",
  "cgm_parse_error": "<string or null>"
}
```

**Validation rules**:
- `nutrition.gi_category` MUST be one of: `"low"`, `"medium"`, `"high"`, or `null`.
- `nutrition.food_items` MUST be a list (may be empty).
- `nutrition.glucose_impact_narrative` MUST reference the 70–140 mg/dL range explicitly.
- `activity.description` MUST be `null` when no activity was logged; `activity.glucose_modulation` MUST be `"No activity logged."`.
- `correlation.summary` MUST contain at least one explicit reference to a food or activity from the session.
- Each `recommendations[].text` MUST reference a specific food, activity type, or timing pattern from the session.
- `glucose_curve` MUST have at least one entry with a non-null `curve_shape_label` when `cgm_parseable = true`.

---

## Token Budget

| Field | Estimated tokens |
|---|---|
| System prompt | ~400 input |
| Session context text | ~100 input |
| Per food photo (base64 JPEG) | ~800 input |
| Per CGM screenshot (base64 JPEG) | ~800 input |
| Response output | ~1000 |

**Per-session max** (10 food + 4 CGM): ~4000 input + 1000 output = 5000 tokens.
Budget cap enforced by `ai_max_tokens_per_session = 4000` (output tokens only).

**Cost increase vs feature 001**:
- Input: ~500 extra tokens (richer prompt + activity section)
- Output: ~800 extra tokens (richer response)
- Additional cost: ~$0.003/session at Sonnet pricing → $0.15/month at 50 sessions → within cap.
