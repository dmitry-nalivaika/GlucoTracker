# Tasks: 004 — Bot UX: Guided Flow, Action Keyboard, Status Messages & Miro Card Enhancements

**Input**: Design documents from `specs/004-bot-ux-guided-flow-miro-enhancements/`
**Branch**: `004-bot-ux-guided-flow-miro-enhancements`
**TDD**: All test tasks MUST be written and confirmed RED before the corresponding implementation task.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story this task belongs to
- Exact file paths in all descriptions

---

## Phase 1: Setup

**Purpose**: No new project infrastructure needed — extends existing codebase.

- [ ] T001 Verify branch is `004-bot-ux-guided-flow-miro-enhancements` and `main` is pulled

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: `chat_id` column + model + repository methods that US1, US2, and contract tests all depend on.

**⚠️ CRITICAL**: US2 (broadcast) cannot be implemented until this phase is complete.

- [ ] T002 [P] Add `chat_id: Mapped[int | None]` field to `User` model in `src/glucotrack/models/user.py`
- [ ] T003 [P] Create Alembic migration `alembic/versions/004_add_chat_id.py` (revision `004`, down_revision `003`; `op.add_column("users", Column("chat_id", BigInteger, nullable=True))`)
- [ ] T004 Write RED unit tests for `update_chat_id()` and `get_all_with_chat_id()` in `tests/unit/test_repositories.py` (confirm both tests fail before T005)
- [ ] T005 Implement `update_chat_id(user_id, chat_id)` and `get_all_with_chat_id()` in `src/glucotrack/repositories/user_repository.py` (makes T004 GREEN)

**Checkpoint**: `pytest tests/unit/test_repositories.py -k "chat_id"` passes.

---

## Phase 3: User Story 1 — Guided Conversational Flow + Session Action Keyboard (P1) 🎯 MVP

**Goal**: Users receive step-by-step next-action prompts after each bot interaction, and a
persistent `/done` `/cancel` `/status` reply keyboard is shown when a session opens.

**Independent Test**: Start a session via `/new`, send a food photo, classify as food; confirm ack
contains a next-step hint AND a reply keyboard is present. Confirm `/done` button dismisses it.

### Tests for US1 (write first — RED)

- [ ] T006 [P] [US1] Write RED unit tests for guided formatter functions in `tests/unit/test_formatters.py`:
  - `test_fmt_food_ack_guided_en` — ack contains next-step hint in English
  - `test_fmt_food_ack_guided_ru` — ack contains next-step hint in Russian
  - `test_fmt_cgm_ack_guided_en` — CGM ack contains next-step hint
  - `test_fmt_activity_ack_guided_en` — activity ack contains next-step hint
  - `test_fmt_new_session_guided_en` — new-session message contains food-photo prompt

### Implementation for US1

- [ ] T007 [US1] Add guided-prompt i18n strings to `src/glucotrack/bot/i18n.py`:
  - `"food_ack_next_step"` — "Add another food photo, send a CGM screenshot, or tap /done."
  - `"cgm_ack_next_step"` — "Add another CGM, describe your activity, or tap /done."
  - `"activity_ack_next_step"` — "Add more photos if needed, or tap /done for your analysis."
  - `"session_start_prompt"` — "Send me a food photo to start logging your meal."
  - Russian translations for all four keys
- [ ] T008 [US1] Add guided formatter functions to `src/glucotrack/bot/formatters.py`:
  - `fmt_food_ack(description, *, lang, guided=True)` — append next-step hint when `guided=True`
  - `fmt_cgm_ack(timing_label, *, lang, guided=True)` — append next-step hint
  - `fmt_activity_ack(text, *, lang, guided=True)` — append next-step hint
  - `fmt_session_start_prompt(*, lang)` — standalone session-start guidance
  - (Makes T006 GREEN)
- [ ] T009 [US1] Add `_session_action_keyboard(lang)` helper to `src/glucotrack/bot/handlers.py` returning `ReplyKeyboardMarkup([["/done", "/cancel", "/status"]], resize_keyboard=True)`
- [ ] T010 [US1] Update `handle_new_session` in `src/glucotrack/bot/handlers.py` to send a second message with `fmt_session_start_prompt(lang=lang)` and `reply_markup=_session_action_keyboard(lang)` after the "new session started" ack
- [ ] T011 [US1] Update `handle_photo_type_callback` in `src/glucotrack/bot/handlers.py` to pass `guided=True` to `fmt_food_ack` and add `reply_markup=_session_action_keyboard(lang)` to the edited message (food branch) or reply (not-sure branch)
- [ ] T012 [US1] Update `_save_cgm` in `src/glucotrack/bot/handlers.py` to pass `guided=True` to `fmt_cgm_ack` and attach `reply_markup=_session_action_keyboard(lang)`
- [ ] T013 [US1] Update `handle_activity_text` in `src/glucotrack/bot/handlers.py` to pass `guided=True` to `fmt_activity_ack` and attach `reply_markup=_session_action_keyboard(lang)`
- [ ] T014 [US1] Ensure `handle_done` and `handle_cancel` call `reply_markup=ReplyKeyboardRemove()` (already present in cancel; add to done's analysis-queued reply in `src/glucotrack/bot/handlers.py`)

**Checkpoint**: `pytest tests/unit/test_formatters.py -k "guided"` passes. Manual test: `/new` shows action keyboard; acks contain hints; `/done` removes keyboard.

---

## Phase 4: User Story 2 — Bot Online/Offline Status Messages (P2)

**Goal**: Users with a stored `chat_id` receive "🟢 GlucoTrack is online!" when the bot starts.

**Independent Test**: Mock `get_all_with_chat_id()` returning two users; call the broadcast
helper; verify both users received the online message.

### Tests for US2 (write first — RED)

- [ ] T015 [US2] Write RED unit tests for broadcast logic in `tests/integration/test_bot_status.py`:
  - `test_online_broadcast_sends_to_all_users_with_chat_id` — mock bot + repo; verify messages sent
  - `test_online_broadcast_is_fire_and_forget` — verify startup is not blocked on send errors

### Implementation for US2

- [ ] T016 [US2] Add `"bot_online"` and `"bot_offline"` i18n strings to `src/glucotrack/bot/i18n.py` (en + ru)
- [ ] T017 [US2] Add `fmt_bot_online(*, lang)` and `fmt_bot_offline(*, lang)` to `src/glucotrack/bot/formatters.py`
- [ ] T018 [US2] Add `store_chat_id_if_changed` helper call in `handle_start` in `src/glucotrack/bot/handlers.py`: after ensuring the user exists, call `user_repo.update_chat_id(user_id, update.effective_chat.id)` if `effective_chat` is not None
- [ ] T019 [US2] Add `_broadcast_online` async function to `src/glucotrack/bot/application.py` that queries `get_all_with_chat_id()`, sends `fmt_bot_online` to each, wrapped in `asyncio.gather` (errors swallowed)
- [ ] T020 [US2] Wire `_broadcast_online` as a PTB `post_init` hook in `create_application` in `src/glucotrack/bot/application.py` (makes T015 GREEN)

**Checkpoint**: `pytest tests/integration/test_bot_status.py` passes.

---

## Phase 5: User Story 3 — Miro Card Enhancements (P3)

**Goal**: Miro cards show (a) all photos in one horizontal row, (b) RAG glucose status badge,
(c) a new grey executive summary + encouragement sticky note.

**Independent Test**: Unit-test each of the three Miro sub-changes independently using the
existing mock analysis fixture in `tests/unit/test_miro_service.py`.

### Tests for US3 (write first — RED)

- [ ] T021 [P] [US3] Write RED unit tests for RAG badge in `tests/unit/test_miro_service.py`:
  - `test_rag_badge_green_when_all_in_range` — all `in_range=True` → 🟢
  - `test_rag_badge_amber_when_half_in_range` — 50 % → 🟡
  - `test_rag_badge_red_when_mostly_out` — < 50 % → 🔴
  - `test_rag_badge_unknown_when_no_data` — no `in_range` values → ⬜
- [ ] T022 [P] [US3] Write RED unit tests for executive summary section in `tests/unit/test_miro_service.py`:
  - `test_executive_summary_section_contains_summary_text`
  - `test_executive_summary_section_contains_encouragement_text`
  - `test_executive_summary_section_fallback_when_fields_absent`
- [ ] T023 [P] [US3] Write RED unit tests for single-row layout in `tests/unit/test_miro_service.py`:
  - `test_single_row_layout_positions_all_images_in_row_0`
  - `test_single_row_frame_width_scales_with_image_count`
- [ ] T024 [P] [US3] Write RED contract test for new AI fields in `tests/contract/test_claude_enhanced_api_schema.py`:
  - `test_executive_summary_field_present`
  - `test_encouragement_field_present`

### Implementation for US3

- [ ] T025 [P] [US3] Add `"executive_summary"` and `"encouragement"` to `SESSION_ANALYSIS_SYSTEM_PROMPT` in `src/glucotrack/services/ai_service.py` (makes T024 GREEN)
- [ ] T026 [P] [US3] Add i18n strings to `src/glucotrack/bot/i18n.py`:
  - `"miro_summary_header"` (en: `"**Session Summary"`, ru: `"**Итоги сессии"`)
  - `"miro_summary_unavailable"` (en/ru fallback)
  - `"miro_encouragement_unavailable"` (en/ru fallback)
- [ ] T027 [US3] Add `_compute_rag_badge(glucose_curve: list) -> str` helper in `src/glucotrack/services/miro_service.py` and call it at the top of the `section == "glucose"` branch in `_build_section_text` (makes T021 GREEN)
- [ ] T028 [US3] Add `section == "summary"` branch to `_build_section_text` in `src/glucotrack/services/miro_service.py`: parse `executive_summary` and `encouragement` from `analysis.raw_response`; fall back to i18n strings if absent (makes T022 GREEN)
- [ ] T029 [US3] Update `create_enhanced_session_card` in `src/glucotrack/services/miro_service.py`:
  - Compute `images_per_row = max(1, len(ordered_images))` (single row)
  - Compute `frame_width = max(1200, images_per_row * 300 + 40)` (dynamic width)
  - Update frame creation call and image position computation to use `frame_width` and `images_per_row`
  - (Makes T023 GREEN)
- [ ] T030 [US3] Add `("summary", 3, "full")` entry to `section_grid` in `create_enhanced_session_card` in `src/glucotrack/services/miro_service.py`; position it centred below row 2 at x = `frame_width // 2`; use `_STYLE_SEPARATOR` (grey); update `n_section_rows = 4` in frame height calculation

**Checkpoint**: `pytest tests/unit/test_miro_service.py tests/contract/test_claude_enhanced_api_schema.py` passes.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T031 Run `ruff check src/ tests/` and fix all errors
- [ ] T032 Run `black src/ tests/` to auto-format
- [ ] T033 Run `mypy src/` and resolve any new type errors
- [ ] T034 Run `pytest tests/ -q --cov-fail-under=80` — confirm ≥ 80 % coverage and all tests green
- [ ] T035 Commit all changes to `004-bot-ux-guided-flow-miro-enhancements` and open PR against `main`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1; BLOCKS US2 (broadcast uses `chat_id`)
- **Phase 3 (US1)**: Depends on Phase 2 for model/migration; independent of US2, US3
- **Phase 4 (US2)**: Depends on Phase 2 (`update_chat_id`, `get_all_with_chat_id` must exist)
- **Phase 5 (US3)**: Independent of US1/US2 — all Miro changes are in separate modules
- **Phase 6 (Polish)**: Depends on all phases complete

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 (model + migration); independent of US2/US3
- **US2 (P2)**: Depends on Phase 2 (repository methods)
- **US3 (P3)**: No dependencies on US1/US2 — entirely in `ai_service.py` and `miro_service.py`

### Parallel Opportunities

- T002 and T003 can run in parallel (different files)
- T006 and T015 and T021–T024 can all run in parallel (all in different test files, no dependencies)
- T025 and T026 and T027 can run in parallel (different files)

---

## Parallel Example: US3

```bash
# All these test tasks can run in parallel (different test classes/files):
Task T021: RAG badge tests in tests/unit/test_miro_service.py
Task T022: Executive summary tests in tests/unit/test_miro_service.py
Task T023: Single-row layout tests in tests/unit/test_miro_service.py
Task T024: Contract test in tests/contract/test_claude_enhanced_api_schema.py

# Then implementation tasks in parallel:
Task T025: Update ai_service.py prompt
Task T026: Add miro i18n strings to i18n.py
# Then sequentially:
Task T027: RAG badge helper in miro_service.py
Task T028: Summary section in miro_service.py
Task T029: Single-row photo layout in miro_service.py
Task T030: Add summary to section_grid in miro_service.py
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 2 (Foundational — T002–T005)
2. Complete Phase 3 (US1 — T006–T014)
3. **STOP and VALIDATE**: guided acks + action keyboard working
4. Proceed to US2 and US3

### Incremental Delivery

1. Foundation → US1 (guided flow) → Deploy/Demo (users see better guidance)
2. Add US2 (online broadcast) → Users know bot status
3. Add US3 (Miro enhancements) → Richer Miro cards

---

## Notes

- TDD is mandatory: every test task (T004, T006, T015, T021–T024) MUST be written and confirmed RED before the implementation task that makes it GREEN
- `handle_start` and `handle_new_session` both touch `handlers.py` — do not run T010 and T018 in parallel
- The `fmt_food_ack`, `fmt_cgm_ack`, `fmt_activity_ack` changes in T008 must maintain backward-compatible signatures (`guided=True` as keyword-only with default)
- The `_IMAGES_PER_ROW` constant in `miro_service.py` becomes unused — remove it in T029 to avoid lint errors
