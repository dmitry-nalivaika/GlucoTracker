# Contract: Claude API Schema

**Feature**: 001-telegram-mvp-session-logging | **Date**: 2026-04-17
**Model**: `claude-3-5-sonnet-20241022` | **SDK**: `anthropic` v0.40+

---

## Session Analysis Request

**Endpoint**: `POST /v1/messages` (via anthropic SDK `client.messages.create`)

### Input Schema

```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 4000,
  "system": "<SYSTEM_PROMPT>",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Session context: [activity description if any]. CGM timing labels: [list of labels]."
        },
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "<base64_encoded_food_photo>"
          }
        },
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "<base64_encoded_cgm_screenshot>"
          }
        }
      ]
    }
  ]
}
```

**Notes**:
- One `image` content block per food photo (may be multiple).
- One `image` content block per CGM screenshot (may be multiple).
- Text block includes activity description and timing labels for CGM entries.
- `max_tokens` hard-capped at 4000 per session (Constitution VII cost guard).

### System Prompt Contract

The system prompt MUST instruct Claude to return a JSON response with exactly this structure:

```json
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
      "in_range": <boolean or null>,
      "notes": "<string>"
    }
  ],
  "correlation": {
    "spikes": ["<description string>"],
    "dips": ["<description string>"],
    "stable_zones": ["<description string>"],
    "summary": "<string>"
  },
  "recommendations": [
    {
      "priority": <1-5 integer>,
      "text": "<actionable recommendation string>"
    }
  ],
  "target_range_note": "<string summarising 70-140 mg/dL compliance>",
  "cgm_parseable": <boolean>,
  "cgm_parse_error": "<string or null>"
}
```

**Contract rules**:
- `cgm_parseable: false` triggers FR-011 graceful degradation flow.
- `glucose_curve[].in_range` is `true` if `estimated_value_mg_dl` is in [70, 140].
- All number fields may be `null` if Claude cannot estimate them from the image.
- `recommendations` MUST contain at least one item if `cgm_parseable: true`.

---

## Trend Analysis Request

### Input Schema

```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 4000,
  "system": "<TREND_SYSTEM_PROMPT>",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "<JSON array of prior session analysis summaries>"
        }
      ]
    }
  ]
}
```

### Expected Response Schema

```json
{
  "period_description": "<string e.g. 'based on your last 7 days'>",
  "session_count": <integer>,
  "stability_trend": "<improving|worsening|stable>",
  "patterns": {
    "stable": ["<food or activity pattern correlated with 70-140 mg/dL>"],
    "spikes": ["<food or activity pattern correlated with spikes>"],
    "dips": ["<food or activity pattern correlated with dips>"]
  },
  "recommendations": [
    {
      "priority": <1-5 integer>,
      "text": "<actionable recommendation>"
    }
  ],
  "target_range_note": "<string: reference to 70-140 mg/dL target>"
}
```

**Contract rules**:
- `patterns.stable`, `patterns.spikes`, `patterns.dips` each MUST contain at least one item.
- `recommendations` MUST contain at least one item.
- `target_range_note` MUST NOT be null or empty.

---

## Error Handling Contract

| Claude API error | System behaviour |
|---|---|
| `APIStatusError` (4xx/5xx) | Retry once after 2s; if still failing, preserve session, notify user to retry |
| Timeout (> 30s) | Cancel task, preserve session, notify user |
| Response JSON parse failure | Log raw response, treat as analysis failure, notify user (FR-011 path) |
| `cgm_parseable: false` in response | Do NOT treat as error; deliver partial analysis with re-submission prompt |
