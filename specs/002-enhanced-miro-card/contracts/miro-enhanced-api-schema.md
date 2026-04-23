# Contract: Miro Enhanced API Schema

**Feature**: 002-enhanced-miro-card | **Date**: 2026-04-23
**API**: Miro REST API v2 | **Auth**: Developer access token (Bearer)

This contract REPLACES the session card portion of `specs/001-telegram-mvp-session-logging/contracts/miro-api-schema.md` for all sessions analysed after feature 002 is deployed.

---

## Step 1: Create Frame Container

**Endpoint**: `POST https://api.miro.com/v2/boards/{board_id}/frames`

### Request Schema
```json
{
  "data": {
    "title": "GlucoTrack Session — {YYYY-MM-DD HH:MM UTC} [User #{anonymised_id}]",
    "format": "custom",
    "type": "freeform"
  },
  "position": {
    "x": 0,
    "y": 0,
    "origin": "center"
  },
  "geometry": {
    "width": 1200,
    "height": 800
  }
}
```

**Notes**:
- `{anonymised_id}` = SHA-256 hash of `user_id`, first 8 hex chars.
- Width is fixed at 1200. Height is calculated: `100 + ceil(n_images / 4) * 320 + 6 * 160`.
- Position is auto-incremented by `y += 900` for each new session to avoid overlap.

### Expected Response (201 Created)
```json
{
  "id": "<frame_id>",
  "type": "frame",
  "data": { "title": "...", "format": "custom", "type": "freeform" },
  "links": { "self": "https://api.miro.com/v2/boards/{board_id}/frames/{frame_id}" }
}
```
The `id` is stored in `miro_cards.miro_card_id`.

---

## Step 2: Upload Session Photos as Image Items

**Endpoint**: `POST https://api.miro.com/v2/boards/{board_id}/images`
**Content-Type**: `multipart/form-data`

### Form Fields
- `data` (JSON string):
```json
{
  "title": "{food|cgm}_{idx+1}",
  "position": { "x": {20 + idx*300}, "y": 100, "relativeTo": "parent_top_left" },
  "geometry": { "width": 280 },
  "parent": { "id": "{frame_id}" }
}
```
- `resource`: binary image bytes (JPEG or PNG)

### Image Ordering
- Food photos first (indices 0–N_food−1), then CGM screenshots (indices N_food–total−1).
- `idx` is the absolute zero-based index across both types.
- Maximum: 10 food photos + 4 CGM screenshots = 14 images per session.

### Expected Response (201 Created)
```json
{
  "id": "<image_item_id>",
  "type": "image",
  "data": { "title": "...", "imageUrl": "...", "createdAt": "..." },
  "parent": { "id": "{frame_id}", "links": {...} }
}
```

### Image Upload Failure Handling (FR-011)
If any image upload returns a non-201 status OR throws a network error:
- Do NOT abort card creation.
- Add a placeholder sticky note at the same position (Step 3 variant).
- Log the failure with `WARNING` level including `telegram_file_id` and HTTP status.

---

## Step 3: Add Analysis Text Sections as Sticky Notes

**Endpoint**: `POST https://api.miro.com/v2/boards/{board_id}/sticky_notes`

One API call per section (6 total: 1 separator + 5 analysis sections).

### Separator
```json
{
  "data": {
    "content": "─── Analysis ───────────────────────",
    "shape": "rectangle"
  },
  "style": { "fillColor": "#e6e6e6", "textColor": "#333333" },
  "position": { "x": 600, "y": {image_section_bottom + 20}, "relativeTo": "parent_top_left" },
  "geometry": { "width": 1160, "height": 40 },
  "parent": { "id": "{frame_id}" }
}
```

### Five Analysis Sections (Food, Activity, Glucose Chart, Correlation Insight, Recommendations)
```json
{
  "data": {
    "content": "**{SECTION_TITLE}**\n\n{section_text}",
    "shape": "rectangle"
  },
  "style": { "fillColor": "#f7f7f7", "textColor": "#1a1a1a" },
  "position": { "x": 600, "y": {y_offset}, "relativeTo": "parent_top_left" },
  "geometry": { "width": 1160, "height": 150 },
  "parent": { "id": "{frame_id}" }
}
```

`y_offset` increments by 170 per section (150 height + 20 gap).

### Image Upload Failure Placeholder (FR-011)
```json
{
  "data": {
    "content": "⚠️ Image unavailable\n(upload failed)",
    "shape": "rectangle"
  },
  "style": { "fillColor": "#fff3cd", "textColor": "#856404" },
  "position": { "x": {same as failed image}, "y": 100, "relativeTo": "parent_top_left" },
  "geometry": { "width": 280, "height": 280 },
  "parent": { "id": "{frame_id}" }
}
```

---

## Error Handling Contract

| HTTP status | Meaning | Behaviour |
|---|---|---|
| `201 Created` | Success | Continue to next step |
| `400 Bad Request` | Malformed payload | Log error, skip item, use placeholder for images |
| `401 Unauthorized` | Invalid token | Log + alert operator; abort entire card creation |
| `404 Not Found` | Board/frame not found | Log + alert operator; abort |
| `413 Payload Too Large` | Image > 6 MB | Use placeholder for that image, continue |
| `429 Too Many Requests` | Rate limit | Retry after `Retry-After` header (max 3×) |
| `5xx Server Error` | Miro outage | Retry with exponential backoff (1s, 2s, 4s) |

**Contract rule**: Frame creation abort propagates to full card failure. Image upload failure uses placeholder. Section text failure uses fallback "Analysis unavailable" text.

---

## Auth Requirements
- Header: `Authorization: Bearer {MIRO_ACCESS_TOKEN}`
- Scope: `boards:write`
