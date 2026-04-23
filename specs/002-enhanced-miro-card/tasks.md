# Tasks: Enhanced Miro Board Card with Embedded Photos and Rich AI Analysis

**Input**: Design documents from `/specs/002-enhanced-miro-card/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: TDD is mandatory per Constitution V. Test tasks precede every implementation task.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

---

## Phase 1: Setup

**Purpose**: Branch and repository setup (already done — branch `002-enhanced-miro-card` exists).

- [ ] T001 Verify branch `002-enhanced-miro-card` is active and `001-telegram-mvp-session-logging` tests pass via `pytest tests/ -q --no-cov`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data layer and AI prompt changes that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Write failing test for `activity_json` field on `AIAnalysis` model in `tests/unit/test_repositories.py` — assert `AnalysisRepository.save_analysis()` accepts and persists `activity_json`
- [ ] T003 Add `activity_json: Mapped[str | None]` column (TEXT, nullable) to `AIAnalysis` in `src/glucotrack/models/analysis.py`
- [ ] T004 Create Alembic migration `alembic/versions/002_add_activity_json.py` — `op.add_column("ai_analyses", sa.Column("activity_json", sa.Text(), nullable=True))`
- [ ] T005 Update `AnalysisRepository.save_analysis()` in `src/glucotrack/repositories/analysis_repository.py` to accept `activity_json: str | None = None` and persist it
- [ ] T006 Run `pytest tests/unit/test_repositories.py -q --no-cov` — all tests must pass
- [ ] T007 Write failing contract test asserting the enhanced Claude API response schema contains `activity`, `nutrition.gi_category`, `nutrition.food_items`, `nutrition.glucose_impact_narrative`, `glucose_curve[].curve_shape_label` in `tests/contract/test_claude_enhanced_api_schema.py`
- [ ] T008 [P] Update `SESSION_ANALYSIS_SYSTEM_PROMPT` in `src/glucotrack/services/ai_service.py` with enhanced JSON schema:
  - Add `activity` section: `description`, `glucose_modulation`, `effect_summary`
  - Add to `nutrition`: `gi_category` ("low"/"medium"/"high"/null), `food_items` (list), `glucose_impact_narrative`
  - Add to each `glucose_curve` entry: `curve_shape_label`
  - Strengthen `correlation.summary` and `recommendations[].text` with session-specific language requirements
- [ ] T009 Update `AnalysisService.run_analysis()` in `src/glucotrack/services/analysis_service.py` to extract `result.get("activity")` and pass as `activity_json=json.dumps(result.get("activity", {}))` to `save_analysis()`
- [ ] T010 Update `formatters.fmt_analysis_result()` in `src/glucotrack/bot/formatters.py` to include Activity section — handles `analysis.activity_json is None` gracefully for backward compatibility
- [ ] T011 Write/update unit tests for enhanced `fmt_analysis_result()` in `tests/unit/test_formatters.py` — assert Activity section appears when `activity_json` present, absent gracefully when `None`
- [ ] T012 Run `pytest tests/ -q --no-cov` — all existing tests must pass (112+ passing, no regressions)

**Checkpoint**: Data layer ready, AI prompt extended, formatters updated. User story implementation can begin.

---

## Phase 3: User Story 1 — View Full Session as a Visual Miro Card (Priority: P1) 🎯 MVP

**Goal**: Create a Miro Frame containing all session photos (food + CGM) as embedded Image items and all five analysis sections as Sticky Note items. This is the complete enhanced card.

**Independent Test**: Complete a session with one food photo and one CGM screenshot, run the analysis pipeline with mocked AI and real DB, assert `MiroService.create_enhanced_session_card()` is called and the mocked Miro API receives:
1. `POST /v2/boards/{board_id}/frames` → frame creation
2. `POST /v2/boards/{board_id}/images` × 2 (food + CGM)
3. `POST /v2/boards/{board_id}/sticky_notes` × 6 (separator + 5 sections)

### Tests for User Story 1

> **Write these tests FIRST — confirm they FAIL before implementation**

- [ ] T013 [P] [US1] Write contract test for Miro frame creation and image upload endpoints in `tests/contract/test_miro_enhanced_api_schema.py`:
  - Mock `POST /v2/boards/{board_id}/frames` → assert request body has `data.title`, `geometry.width=1200`
  - Mock `POST /v2/boards/{board_id}/images` multipart → assert `parent.id` is set to frame ID
  - Mock `POST /v2/boards/{board_id}/sticky_notes` → assert `parent.id` is frame ID, `data.content` contains section title
  - Use `respx` to mock all httpx calls
- [ ] T014 [P] [US1] Write unit tests for `MiroService.create_enhanced_session_card()` in `tests/unit/test_miro_service.py`:
  - `test_creates_frame_first()` — frame POST called before any image POST
  - `test_uploads_food_photos_before_cgm()` — food images uploaded first (FR-002)
  - `test_image_failure_adds_placeholder()` — when image upload returns 413, sticky note placeholder is added (FR-011)
  - `test_all_five_sections_created()` — six sticky note calls (separator + 5 sections) after images
  - `test_returns_frame_id()` — return value is the frame ID from the frame creation response
  - `test_card_not_blocked_by_single_image_failure()` — remaining images and sections still created
- [ ] T015 [P] [US1] Write integration test in `tests/integration/test_analysis_flow.py` — `test_analysis_calls_enhanced_miro_card()`:
  - Patch `MiroService.create_enhanced_session_card` (async mock)
  - Run `AnalysisService.run_analysis()` end-to-end with test DB
  - Assert `create_enhanced_session_card` was called with correct `user_id`, `session_id`, `analysis` object, and `session_images` list containing dicts with `type`, `file_bytes`, `telegram_file_id`

### Implementation for User Story 1

- [ ] T016 [US1] Add `_create_frame()` private method to `MiroService` in `src/glucotrack/services/miro_service.py`:
  - `POST /v2/boards/{board_id}/frames`
  - Payload: `data.title`, `data.format="custom"`, `data.type="freeform"`, `position`, `geometry`
  - Returns frame ID (str)
  - Uses existing retry logic (429, 5xx)
- [ ] T017 [US1] Add `_upload_image()` private method to `MiroService`:
  - `POST /v2/boards/{board_id}/images` with `multipart/form-data`
  - Fields: `data` (JSON string with position, parent.id, geometry.width=280), `resource` (bytes)
  - Returns image item ID (str) on 201, `None` on failure (413/400/network)
  - Logs WARNING with `telegram_file_id` and HTTP status on failure
- [ ] T018 [US1] Add `_add_sticky_note()` private method to `MiroService`:
  - `POST /v2/boards/{board_id}/sticky_notes`
  - Payload: `data.content`, `data.shape="rectangle"`, `style`, `position` (with `relativeTo="parent_top_left"`), `geometry`, `parent.id`
  - Returns sticky note ID (str)
  - Raises `MiroError` on unrecoverable failure (caught by caller)
- [ ] T019 [US1] Implement `create_enhanced_session_card()` in `MiroService`:
  - Signature: `async def create_enhanced_session_card(self, analysis: Any, session_images: list[dict[str, Any]]) -> str`
  - Step 1: Call `_create_frame()` → get `frame_id`
  - Step 2: Loop over `session_images` (food first, then cgm per FR-002); call `_upload_image()` per image; on `None` result call `_add_sticky_note()` with placeholder text (FR-011)
  - Step 3: Calculate `y_offset` after image rows
  - Step 4: Add separator sticky note
  - Step 5: Add Food, Activity, Glucose Chart, Correlation Insight, Recommendations sections via `_add_sticky_note()` using `_build_section_text(analysis, section_name)` helper
  - Returns `frame_id`
  - The old `create_session_card()` remains for backward compatibility but is no longer called by new code
- [ ] T020 [US1] Add `_build_section_text()` private method to `MiroService`:
  - Accepts `analysis: Any` and `section: str` ("food", "activity", "glucose", "correlation", "recommendations")
  - Parses the appropriate JSON column from `analysis`
  - Returns formatted string with section header and content
  - Falls back to `"Analysis unavailable for this section — please re-submit your session."` if JSON is None/invalid
- [ ] T021 [US1] Update `AnalysisService.run_analysis()` in `src/glucotrack/services/analysis_service.py`:
  - After loading session entries, collect `session_images`: list of `{"type": "food"|"cgm", "file_bytes": bytes, "telegram_file_id": str}` using `load_file_bytes()`
  - Replace `self._miro.create_session_card(analysis=analysis)` with `self._miro.create_enhanced_session_card(analysis=analysis, session_images=session_images)`
- [ ] T022 [US1] Run `pytest tests/ -q --no-cov` — all tests must pass
- [ ] T023 [US1] Run `ruff check src/ && black --check src/ && mypy src/` — all must pass

**Checkpoint**: Full enhanced Miro Frame card is created with images and all 5 sections. US1 fully functional.

---

## Phase 4: User Story 2 — Understand Food Impact (Priority: P2)

**Goal**: The Food section on the Miro card displays identified food items, nutritional breakdown with GI category, and a glucose impact narrative referencing 70–140 mg/dL.

**Independent Test**: Assert the Food section sticky note content on the Miro card contains:
- Identified food items (from `nutrition.food_items`)
- Carbs/proteins/fats/GI category (from `nutrition`)
- Glucose impact narrative mentioning "70" or "140" (from `nutrition.glucose_impact_narrative`)

### Tests for User Story 2

- [ ] T024 [P] [US2] Extend `tests/unit/test_miro_service.py` with `test_food_section_contains_gi_category_and_items()`:
  - Mock `analysis.nutrition_json` with `food_items`, `gi_category`, `glucose_impact_narrative` present
  - Call `_build_section_text(analysis, "food")`
  - Assert output contains GI category text, food item names, and narrative text

### Implementation for User Story 2

- [ ] T025 [US2] Update `_build_section_text()` for "food" section in `src/glucotrack/services/miro_service.py`:
  - Format: `**Food\n\nItems: {food_items_joined}\nCarbs: {carbs_g}g | Protein: {proteins_g}g | Fat: {fats_g}g | GI: {gi_category} (~{gi_estimate})\n\n{glucose_impact_narrative}`
  - Handle missing fields gracefully (`"?" `if null)
- [ ] T026 [US2] Run `pytest tests/unit/test_miro_service.py -q --no-cov` — pass

**Checkpoint**: Food section on card contains all required content per FR-005 and US2 acceptance scenarios.

---

## Phase 5: User Story 3 — Understand Glucose Response (Priority: P3)

**Goal**: The Glucose Chart section lists glucose readings per timing point, evaluates each against 70–140 mg/dL, and includes a curve shape label.

**Independent Test**: Assert the Glucose Chart section sticky note content contains at least one numeric glucose value, a statement about in/out of 70–140 mg/dL range, and a `curve_shape_label`.

### Tests for User Story 3

- [ ] T027 [P] [US3] Extend `tests/unit/test_miro_service.py` with `test_glucose_section_contains_range_and_curve_label()`:
  - Mock `analysis.glucose_curve_json` with entries that have `in_range`, `estimated_value_mg_dl`, `curve_shape_label`
  - Assert section text contains "mg/dL", range assessment, and curve shape label
  - Also test: unparseable CGM → section contains "unreadable" advisory (per spec edge case)

### Implementation for User Story 3

- [ ] T028 [US3] Update `_build_section_text()` for "glucose" section in `src/glucotrack/services/miro_service.py`:
  - Format per reading: `{timing_label}: {estimated_value_mg_dl} mg/dL — {in_range and "✅ in range" or "⚠️ out of range"} | Shape: {curve_shape_label}`
  - When `cgm_parseable = false`: display `"⚠️ CGM unreadable: {cgm_parse_error}. Please re-submit a clearer screenshot."`
- [ ] T029 [US3] Run `pytest tests/unit/test_miro_service.py -q --no-cov` — pass

**Checkpoint**: Glucose Chart section contains per-point readings with range assessment and curve label per FR-007 and US3.

---

## Phase 6: User Story 4 — Cause-and-Effect Correlation Insight (Priority: P4)

**Goal**: The Correlation Insight section contains explicit cause-effect statements referencing specific foods and activities from the session.

**Independent Test**: Assert the Correlation Insight section contains at least two statements from `correlation.spikes` or `correlation.dips` (cause-effect list) plus the `correlation.summary`.

### Tests for User Story 4

- [ ] T030 [P] [US4] Extend `tests/unit/test_miro_service.py` with `test_correlation_section_includes_spikes_and_summary()`:
  - Mock `analysis.correlation_json` with `spikes`, `dips`, `stable_zones`, `summary`
  - Assert all non-empty lists are rendered and `summary` is present

### Implementation for User Story 4

- [ ] T031 [US4] Update `_build_section_text()` for "correlation" section in `src/glucotrack/services/miro_service.py`:
  - Format: section title + spikes list + dips list + stable zones list + summary paragraph
  - Skip empty lists gracefully
  - Fallback if no activity: display correlation summary only (no fabricated activity text per US4 AC3)
- [ ] T032 [US4] Run `pytest tests/unit/test_miro_service.py -q --no-cov` — pass

**Checkpoint**: Correlation Insight section shows explicit cause-effect statements per FR-008 and US4.

---

## Phase 7: User Story 5 — Actionable Recommendations (Priority: P5)

**Goal**: The Recommendations section contains at least one session-specific, actionable suggestion that references the meal or activity, with the goal of maintaining 70–140 mg/dL.

**Independent Test**: Assert the Recommendations section text contains at least one recommendation from `recommendations` list, formatted as a numbered/bulleted list, with the first item visually prominent.

### Tests for User Story 5

- [ ] T033 [P] [US5] Extend `tests/unit/test_miro_service.py` with `test_recommendations_section_formats_list()`:
  - Mock `analysis.recommendations_json` with 2–3 items of varying priority
  - Assert section renders items in priority order and each is a distinct line

### Implementation for User Story 5

- [ ] T034 [US5] Update `_build_section_text()` for "recommendations" section in `src/glucotrack/services/miro_service.py`:
  - Sort by `priority` ascending
  - Format: `1. {text}\n2. {text}...`
  - Fallback if empty list: `"No specific recommendations generated for this session."`
- [ ] T035 [US5] Run `pytest tests/unit/test_miro_service.py -q --no-cov` — pass

**Checkpoint**: Recommendations section is well-formatted and prioritised per FR-009 and US5.

---

## Phase 8: Activity Section (Cross-Cutting — supports FR-006)

**Goal**: The Activity sub-section shows activity type/intensity and glucose modulation explanation; displays "No activity logged" when absent (FR-006).

- [ ] T036 [P] Write test in `tests/unit/test_miro_service.py` `test_activity_section_no_activity()`:
  - `analysis.activity_json = json.dumps({"description": null, "glucose_modulation": "No activity logged.", "effect_summary": "..."})`
  - Assert section contains "No activity logged"
- [ ] T037 Update `_build_section_text()` for "activity" section in `src/glucotrack/services/miro_service.py`:
  - When `description` is null/None: display `"No activity logged"`
  - When activity present: display description, glucose_modulation, effect_summary
- [ ] T038 Run `pytest tests/ -q --no-cov` — all pass

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, edge cases, and quality gates.

- [ ] T039 [P] Write integration test `test_image_upload_failure_does_not_abort_card()` in `tests/integration/test_analysis_flow.py`:
  - Mock one image upload to return 413 → assert sticky note placeholder created for that slot
  - Assert remaining images and all 5 sections still created
- [ ] T040 [P] Write contract test asserting `activity` field is present and non-null in the Claude API response schema in `tests/contract/test_claude_enhanced_api_schema.py`
- [ ] T041 [P] Update `MiroCard.status` to `COMPLETED` after successful `create_enhanced_session_card()` in `src/glucotrack/services/analysis_service.py` (addresses Reviewer Agent SUGGESTION from PR #2 about stuck PENDING status)
- [ ] T042 Run full test suite: `pytest tests/ -v` — 80%+ coverage, all pass
- [ ] T043 Run `ruff check src/ && black --check src/ && mypy src/` — all must pass
- [ ] T044 [P] Update `specs/001-telegram-mvp-session-logging/contracts/miro-api-schema.md` with a note that session card creation is superseded by feature 002 for new sessions
- [ ] T045 Commit: `feat(002): implement enhanced Miro card with embedded photos and rich AI analysis`
- [ ] T046 Open PR against `main` with PR template

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** (Setup): No dependencies — start immediately
- **Phase 2** (Foundational): Depends on Phase 1 — BLOCKS all user stories
- **Phase 3** (US1 — Core Frame Card): Depends on Phase 2 — **MVP delivery point**
- **Phases 4–8** (US2–US5 + Activity): Depend on Phase 3 (build on the frame's `_build_section_text`)
- **Phase 9** (Polish): Depends on Phases 3–8

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2 — no dependency on other user stories
- **US2–US5 (P2–P5)**: Each depends only on US1 (the section text builder), otherwise independent
- **Activity (FR-006)**: Parallel to US2–US5

### Within Each Phase

- Tests MUST be written FIRST and confirmed to FAIL before implementation
- Commit after each complete task or logical group
- Run `pytest tests/ -q --no-cov` after each implementation task

---

## Parallel Opportunities

```bash
# Phase 2: Parallel foundational tasks
Task T003: Update AIAnalysis model
Task T007: Write Claude contract test (no code dependency yet)

# Phase 3: Parallel test writing
Task T013: Write Miro contract test
Task T014: Write MiroService unit tests
Task T015: Write AnalysisService integration test

# Phase 4–8: US2–US5 + Activity all depend on T019-T020 only
Task T024: Test for Food section
Task T027: Test for Glucose section
Task T030: Test for Correlation section
Task T033: Test for Recommendations section
Task T036: Test for Activity section
```

---

## Implementation Strategy

### MVP First (US1 Core Card — Phases 1–3)

1. Phase 1: Branch verified
2. Phase 2: Data layer + AI prompt updated
3. Phase 3: Full frame card with images and all 5 sections
4. **STOP and VALIDATE**: Integration test passes; Telegram SLO unaffected
5. This is the full enhanced card — all FRs are partially satisfied

### Incremental Section Quality (Phases 4–8)

Each phase improves the content quality of one section without changing the card structure.
Each is independently committable after tests pass.

---

## Notes

- `[P]` = different files, no intra-phase dependencies — can be parallelised
- TDD: every implementation task must be preceded by a failing test
- `_build_section_text()` is a shared method — test thoroughly in Phase 3 before extending in Phases 4–8
- The old `MiroService.create_session_card()` is NOT deleted — it remains for any trend card usage
- `activity_json` is nullable — all formatters and section builders must handle `None` gracefully
