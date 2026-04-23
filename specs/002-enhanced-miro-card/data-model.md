# Data Model: Enhanced Miro Card

**Feature**: 002-enhanced-miro-card | **Date**: 2026-04-23

---

## Existing Entities (unchanged)

All entities from feature 001 are unchanged:
- `User`, `Session`, `FoodEntry`, `CGMEntry`, `ActivityEntry`
- `MiroCard` — tracks the card creation record; `miro_card_id` now stores the **frame ID**
- `TrendAnalysis`

---

## Modified Entity: AIAnalysis

### Change
Add `activity_json` column to `ai_analyses` table.

```sql
ALTER TABLE ai_analyses ADD COLUMN activity_json TEXT NULL;
```

### Purpose
Stores the AI-generated activity analysis section as JSON:
```json
{
  "description": "30-minute brisk walk after meal",
  "glucose_modulation": "Activity reduced the post-meal glucose spike by accelerating uptake",
  "effect_summary": "Moderate glucose-lowering effect observed at the 1-hour mark"
}
```

**Nullable**: `True` — pre-002 sessions that have `AIAnalysis` rows without this field remain valid.
The Telegram formatter and Miro service handle `activity_json = None` gracefully.

### Updated SQLAlchemy Model (src/glucotrack/models/analysis.py)
```python
activity_json: Mapped[str | None] = mapped_column(Text, nullable=True)
```

### Alembic Migration
File: `alembic/versions/002_add_activity_json.py`
- Revision ID: `002`
- Revises: `001`
- Operation: `op.add_column("ai_analyses", sa.Column("activity_json", sa.Text(), nullable=True))`

---

## New Spec Entities (design-time only, not ORM models)

The spec defines `EnhancedMiroCard`, `CardImageSlot`, and `CardAnalysisSection` as conceptual
artefacts. These are **not** persisted as separate ORM models — they exist only during the
Miro card creation process:

- `EnhancedMiroCard` = the Miro Frame created at runtime; its ID is stored in `miro_cards.miro_card_id`
- `CardImageSlot` = transient: each food/CGM image item created inside the frame; not separately tracked in DB
- `CardAnalysisSection` = transient: each text/sticky-note item created inside the frame; not separately tracked

The `MiroCard` DB record (`miro_cards` table) captures the top-level frame ID and status.
Individual image slot failures are logged but not persisted individually (no new DB table needed).

**Rationale**: The DB record already tracks the card's existence and status. Individual image
slot tracking would add a new table with no downstream consumer — over-engineering for the MVP.

---

## AI Prompt Output Schema (extended)

The `AIService.analyse_session` response will include the following new / extended fields:

### Extended `nutrition`
```json
{
  "carbs_g": 45,
  "proteins_g": 20,
  "fats_g": 10,
  "gi_estimate": 65,
  "gi_category": "medium",
  "food_items": ["brown rice", "grilled chicken", "salad"],
  "glucose_impact_narrative": "The moderate-GI carbohydrates are expected to cause a gradual rise staying within the 70–140 mg/dL range.",
  "notes": "..."
}
```

### Extended `glucose_curve` entries
```json
{
  "timing_label": "1 hour after",
  "estimated_value_mg_dl": 130,
  "in_range": true,
  "notes": "...",
  "curve_shape_label": "gradual rise with plateau"
}
```

### New `activity` section
```json
{
  "description": "30-minute brisk walk",
  "glucose_modulation": "Post-meal walk reduced the glucose spike via increased uptake",
  "effect_summary": "Moderate glucose-lowering effect; levels returned to baseline 30 min earlier"
}
```
(When no activity: `description: null`, `glucose_modulation: "No activity logged."`, `effect_summary: "No activity to analyse."`)

### Unchanged fields
- `correlation` — already contains cause-effect statements; prompt enforcement ensures session-specific references
- `recommendations` — prompt enforcement ensures session-specific actionable suggestions
- `target_range_note`, `cgm_parseable`, `cgm_parse_error` — unchanged

---

## Storage Path (unchanged)

Session images continue to use the existing path pattern:
```
/users/{user_id}/sessions/{session_id}/{type}_{telegram_file_id}.jpg
```
Images are read by `StorageRepository.load_file()` before being uploaded to Miro.
