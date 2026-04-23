# Research: Enhanced Miro Card with Embedded Photos and Rich AI Analysis

**Feature**: 002-enhanced-miro-card | **Date**: 2026-04-23

---

## 1. Miro API v2 — Image Embedding in Cards

### Finding
The Miro API v2 does NOT have a single widget type that combines both images and rich text
sections inside one card element. Instead, the correct approach is to use a **Frame** as the
container, with child items inside it:

- **Frame** (`POST /v2/boards/{board_id}/frames`) — acts as the "enhanced card" container.
- **Image items** (`POST /v2/boards/{board_id}/images` with `multipart/form-data`) — food photos
  and CGM screenshots uploaded as image widgets parented to the frame.
- **Text/Sticky-note items** (`POST /v2/boards/{board_id}/sticky_notes`) — the five analysis
  sections parented to the frame.

A child item is attached to a frame by including `"parent": {"id": "<frame_id>"}` in the request
body at creation time.

**Decision**: Use Frame + children pattern.
**Rationale**: Only Miro approach that satisfies FR-001 (visible images), FR-003 (two sections),
and FR-004 (five labelled sub-sections) simultaneously.
**Alternatives rejected**: App Cards (no embedded images, needs hosted iFrame), regular Cards
(title + description only, no image support), sticky notes alone (no parent-child layout).

### Spec Assumption Validation
> "The Miro board API supports embedding images as first-class elements within a card frame;
> if the API only supports image links, this assumption is false and the feature scope must be
> revisited during planning."

**Confirmed TRUE**: Miro Frame = "card frame". Image items can be embedded as first-class
children of a Frame, visible without clicking, satisfying the spec requirement.

---

## 2. Image Upload Method

### Finding
The Miro `/v2/boards/{board_id}/images` endpoint accepts two creation methods:
1. **URL-based** (`Content-Type: application/json`): requires a publicly accessible URL.
2. **File upload** (`Content-Type: multipart/form-data`): uploads binary file data directly.

Form fields for file upload:
- `data` (JSON string): position, parent, geometry, title
- `resource` (binary): image file bytes

**Supported formats**: JPEG, PNG, SVG, GIF (standard web image formats).
**Size limit**: 6 MB per file (same as document upload endpoint).

**Decision**: Use multipart/form-data file upload.
**Rationale**: Session photos are stored locally (`/users/{user_id}/sessions/{session_id}/`).
Serving them as public URLs would require a separate hosting layer out of scope for the MVP.
Direct file upload avoids this dependency.
**Alternatives rejected**: URL-based upload (would need public file server), base64 encoding
(not a supported format for the images endpoint).

---

## 3. Frame Layout Design

### Finding
Miro items within a frame use absolute x/y coordinates within the frame's coordinate space.
Items are positioned relative to the frame's top-left corner.

**Chosen layout**:
```
Frame: 1200 × (400 + N_images * 340 + 5 * 160) px
┌─────────────────────────────────────────────┐
│  [HEADER] GlucoTrack Session — {timestamp}  │  y=20,  h=60
│  [Image1] [Image2] [Image3] ...             │  y=100, h=300 per image
│  ─── Analysis ──────────────────────────    │  y=header+images+20
│  [Food]                                     │  h=150
│  [Activity]                                 │  h=150
│  [Glucose Chart]                            │  h=150
│  [Correlation Insight]                      │  h=150
│  [Recommendations]                          │  h=150
└─────────────────────────────────────────────┘
```
Images: 280×280 px each, spaced 20 px, up to 14 images (10 food + 4 CGM) across.

---

## 4. Claude Prompt Enhancement

### Finding
The current `SESSION_ANALYSIS_SYSTEM_PROMPT` returns 4 analysis sections (nutrition,
glucose_curve, correlation, recommendations). Feature 002 requires 5 sections — adding
**Activity** as a dedicated section.

Additional enrichment needed per spec requirements:
- **Nutrition** (FR-005): add `food_items` list, `gi_category` (low/medium/high),
  `glucose_impact_narrative` (blood glucose impact text)
- **Glucose Curve** (FR-007): add `curve_shape_label`, `readings_outside_range` list
- **Correlation** (FR-008): ensure explicit cause-effect phrases (already partially present)
- **Recommendations** (FR-009): ensure session-specific references (already partially present)
- **Activity** (FR-006): new section with `description`, `glucose_modulation`, `effect_summary`

**Decision**: Extend the existing `SESSION_ANALYSIS_SYSTEM_PROMPT` with new fields.
**Rationale**: New fields are backward compatible for downstream consumers (Telegram formatter
reads only the fields it needs). All consumers of `AIAnalysis` use `.get()` on parsed JSON.
**Cost impact estimate**: Richer prompt ≈ +500 input tokens + ~800 output tokens per session.
At Claude Sonnet pricing: ~$0.003 per session additional cost. At 50 sessions/month:
$0.15/month extra → well within $50 cap.

---

## 5. Database Schema Change

### Finding
The enhanced AI response includes an `activity` section. This needs to be persisted in
`AIAnalysis` for:
- Consistency between Telegram and Miro card (FR-010)
- Audit trail of AI-generated activity analysis

**Decision**: Add `activity_json` TEXT column to `ai_analyses` table, nullable.
**Rationale**: Nullable allows old sessions (pre-002) to remain valid without migration data.
**Migration**: Alembic revision `002_add_activity_json.py`.

---

## 6. Retry & Error Handling

### Finding
The existing MiroService retry strategy (429 → Retry-After header, 5xx → exponential backoff)
applies per API call. For the enhanced card (which makes multiple API calls per card), each
call is retried independently. A partial success (frame created, some images failed) is handled
by FR-011: image slot is replaced with a placeholder text item ("image unavailable").

**Decision**: Extend existing retry logic to cover image upload calls. Image upload failures
do NOT abort card creation — a placeholder text item is added instead.

---

## 7. Miro API Rate Limits

### Finding
Miro API v2 uses tiered rate limits:
- **Level 2 endpoints** (images, documents, frames): ~300 requests/10 min per board.
- **Level 3 endpoints** (cards, text, sticky notes): ~600 requests/10 min.

A single enhanced card creation makes at most:
1 frame + 14 images + 6 text items (header + 5 sections) = 21 API calls.
At max 50 sessions/month → ~1050 API calls/month, far below rate limits.

**Decision**: No additional rate limit handling needed beyond existing retry for 429.
