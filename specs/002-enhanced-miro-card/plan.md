# Implementation Plan: Enhanced Miro Board Card with Embedded Photos and Rich AI Analysis

**Branch**: `002-enhanced-miro-card` | **Date**: 2026-04-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-enhanced-miro-card/spec.md`

---

## Summary

Replace the basic Miro card (single card widget with plain text) with a rich **Frame-based card**
containing uploaded session photos as embedded Image items and five formatted analysis sections
as Sticky Note items. Extend the Claude prompt to produce a richer five-section response (adding
Activity) and persist the new `activity_json` field in `AIAnalysis`. Update the Telegram
formatter to include the Activity section for consistency (FR-010).

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: python-telegram-bot 22.x, anthropic SDK, httpx, SQLAlchemy 2.0 async, aiosqlite
**Storage**: SQLite (dev), aiosqlite, local file system for photos
**Testing**: pytest + pytest-asyncio, respx (httpx mocking)
**Target Platform**: Linux server / local dev (macOS)
**Project Type**: Telegram bot service
**Performance Goals**: Miro card created ≤5s from analysis completion (SC-003); Telegram delivery SLO unchanged
**Constraints**: Miro image upload ≤6 MB per file; 14 images max per session; $50/month cost cap
**Scale/Scope**: MVP, ~50 sessions/month

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|---|---|---|
| **I. Vision** — does this align with glucose analysis product? | ✅ PASS | Feature directly advances the core value proposition |
| **II. Multi-user isolation** | ✅ PASS | Images uploaded per user/session path; frame titled with anonymised user ID; no cross-user writes |
| **III. Technology stack** | ✅ PASS | Uses Miro API (bound by constitution), Anthropic API, existing Python services |
| **IV. Feature-based delivery** | ✅ PASS | Feature branch, spec.md, plan.md, tasks.md workflow |
| **V. Code quality** | ✅ PASS | TDD, ruff/black/mypy required; no secrets in code |
| **VI. SLOs** | ✅ PASS | SC-003 ≤5s Miro card; existing Telegram 30s SLO unaffected (fire-and-forget) |
| **VII. Cost guard** | ✅ PASS | +$0.15/month estimated; well within $50 cap |

**Post-design re-check**: ✅ No additional violations after Phase 1.

---

## Project Structure

### Documentation (this feature)
```text
specs/002-enhanced-miro-card/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   ├── miro-enhanced-api-schema.md
│   └── claude-enhanced-api-schema.md
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code Changes (repository root)
```text
src/glucotrack/
├── models/
│   └── analysis.py              # +activity_json column
├── services/
│   ├── ai_service.py            # Enhanced SESSION_ANALYSIS_SYSTEM_PROMPT
│   └── miro_service.py          # New create_enhanced_session_card() replacing create_session_card()
├── services/
│   └── analysis_service.py     # Pass session images to MiroService
├── repositories/
│   └── analysis_repository.py  # +activity_json param in save_analysis()
└── bot/
    └── formatters.py            # +Activity section in fmt_analysis_result()

alembic/versions/
└── 002_add_activity_json.py     # Migration: add activity_json column

tests/
├── unit/
│   ├── test_miro_service.py     # Enhanced service tests
│   ├── test_ai_service.py       # Enhanced prompt schema tests
│   └── test_analysis_service.py # Analysis → Miro wiring tests
├── integration/
│   └── test_analysis_flow.py    # Full pipeline integration tests
└── contract/
    ├── test_miro_enhanced_api_schema.py   # New Miro contract tests
    └── test_claude_enhanced_api_schema.py # Updated Claude contract tests
```

---

## Implementation Phases

### Phase A: Data Layer
1. Add `activity_json` to `AIAnalysis` model (nullable TEXT)
2. Create Alembic migration `002_add_activity_json.py`
3. Update `AnalysisRepository.save_analysis()` to accept and persist `activity_json`

### Phase B: AI Service Enhancement
4. Update `SESSION_ANALYSIS_SYSTEM_PROMPT` with new fields:
   - `activity` section (description, glucose_modulation, effect_summary)
   - `nutrition.gi_category`, `nutrition.food_items`, `nutrition.glucose_impact_narrative`
   - `glucose_curve[].curve_shape_label`
5. Pass `activity_json` through `AnalysisService.run_analysis()` → `save_analysis()`

### Phase C: Telegram Formatter Update
6. Update `formatters.fmt_analysis_result()` to include Activity section (FR-010 consistency)

### Phase D: Enhanced MiroService
7. Add `_create_frame()` helper method
8. Add `_upload_image()` helper — multipart/form-data upload; returns item ID or None on failure
9. Add `_add_sticky_note()` helper — creates text section inside frame
10. Implement `create_enhanced_session_card(analysis, session_images)` that:
    - Creates a frame
    - Uploads food photos + CGM screenshots as image items (food first, then CGM)
    - Handles image failures with placeholder sticky notes (FR-011)
    - Adds 5 analysis sections as sticky notes
    - Returns frame ID

### Phase E: Analysis Service Wiring
11. Update `AnalysisService.run_analysis()` to collect image bytes per entry and pass to
    `create_enhanced_session_card(analysis, session_images)` instead of old `create_session_card()`

### Phase F: Tests (TDD throughout)
Each phase has tests written BEFORE implementation. See tasks.md for per-task test requirements.

---

## Complexity Tracking

No constitution violations.

---

## Key Design Decisions

### Why Frame + children (not a single card widget)?
The Miro API has no single widget that contains both images and rich text. The Frame approach
is the only way to satisfy FR-001 (embedded images) + FR-004 (five labelled sections).

### Why pass `session_images` to MiroService?
`AnalysisService` already loads image bytes via `load_file_bytes()`. Passing them directly
to `MiroService` avoids a second read from disk and keeps the storage access in one place.

### Why add `activity_json` to AIAnalysis?
FR-010 requires Miro card content to be consistent with the Telegram analysis. Persisting
`activity_json` in `AIAnalysis` ensures both outputs use the same AI-generated text.

### Backward compatibility
- `activity_json = None` is valid for all pre-002 sessions.
- `formatters.fmt_analysis_result()` checks `if activity_json else` to avoid breaking
  existing Telegram messages.
- `create_enhanced_session_card()` replaces `create_session_card()` — old sessions are
  not retroactively updated (per spec assumption).
