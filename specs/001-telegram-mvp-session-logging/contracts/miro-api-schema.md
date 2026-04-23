# Contract: Miro API Schema

**Feature**: 001-telegram-mvp-session-logging | **Date**: 2026-04-17
**API**: Miro REST API v2 | **Auth**: Developer access token (Bearer)

> **Note (feature 002)**: The enhanced card format implemented in feature 002 supersedes the
> single-card approach below. `create_enhanced_session_card()` now creates a **frame** containing
> uploaded food/CGM images and five analysis sticky-note sections. See
> `specs/002-enhanced-miro-card/contracts/` for the updated schema. The endpoints below describe
> the original 001 implementation and are retained for historical reference.

---

## Create Session Analysis Card (original — superseded by feature 002)

**Endpoint**: `POST https://api.miro.com/v2/boards/{board_id}/cards`

### Request Schema

```json
{
  "data": {
    "title": "GlucoTrack Session — {YYYY-MM-DD HH:MM UTC} [User #{anonymised_id}]",
    "description": "**Nutrition**: {carbs_g}g carbs, {proteins_g}g protein, {fats_g}g fat, GI ~{gi_estimate}\n\n**Glucose Response**: {glucose_curve_summary}\n\n**Correlation**: {correlation_summary}\n\n**Top Recommendation**: {top_recommendation_text}"
  },
  "position": {
    "x": 0,
    "y": 0,
    "origin": "center"
  },
  "geometry": {
    "width": 320,
    "height": 180
  }
}
```

**Notes**:
- `{anonymised_id}` is a short hash of `user_id` — NEVER the raw Telegram user ID or username.
- `style.fillColor` is not supported by the Miro cards API v2 — omitted from payload.
- Position is auto-placed; Miro positions sequentially if coordinates collide.

### Expected Response (201 Created)

```json
{
  "id": "<miro_card_id>",
  "type": "card",
  "data": { "title": "...", "description": "..." },
  "createdAt": "<ISO8601 datetime>",
  "createdBy": { "id": "...", "type": "user" },
  "links": { "self": "https://api.miro.com/v2/boards/{board_id}/cards/{card_id}" }
}
```

The `id` field is stored in `miro_cards.miro_card_id`.

---

## Create Trend Analysis Card

**Endpoint**: `POST https://api.miro.com/v2/boards/{board_id}/cards`

### Request Schema

```json
{
  "data": {
    "title": "GlucoTrack TREND — {period_description} [User #{anonymised_id}]",
    "description": "**Sessions analysed**: {session_count}\n\n**Stability**: {stability_trend}\n\n**Best patterns**: {stable_patterns_summary}\n\n**Top Recommendation**: {top_recommendation_text}\n\n**Target range (70–140 mg/dL)**: {target_range_note}"
  },
  "position": {
    "x": 400,
    "y": 0,
    "origin": "center"
  },
  "geometry": {
    "width": 320,
    "height": 200
  }
}
```

**Notes**:
- `style.fillColor` is not supported by the Miro cards API v2 — omitted from payload.

---

## Error Handling Contract

| HTTP status | Meaning | System behaviour |
|---|---|---|
| `201 Created` | Success | Store `miro_card_id`, set `miro_cards.status = created` |
| `400 Bad Request` | Malformed payload | Log error, set `status = failed`, do NOT retry |
| `401 Unauthorized` | Invalid/expired token | Log error, alert operator, set `status = failed` |
| `404 Not Found` | Board not found | Log error, alert operator, set `status = failed` |
| `429 Too Many Requests` | Rate limit | Retry after `Retry-After` header delay (max 3 retries) |
| `5xx Server Error` | Miro outage | Retry up to 3× with exponential backoff (1s, 2s, 4s) |

**Contract rule**: Miro failure MUST NOT prevent Telegram delivery of analysis (FR-009). Miro card creation runs as a fire-and-forget background task after Telegram message is sent.

---

## Auth Requirements

- Header: `Authorization: Bearer {MIRO_ACCESS_TOKEN}`
- Required scope: `boards:write`
- `MIRO_ACCESS_TOKEN` and `MIRO_BOARD_ID` sourced from environment variables only — NEVER hardcoded (Constitution V).
