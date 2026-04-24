# Tasks: Russian Language Support (Feature 003)

**Input**: Design documents from `specs/003-russian-language-support/`
**Branch**: `003-russian-language-support`
**TDD**: Write each test first → confirm RED → implement → confirm GREEN → commit

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependency)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup

**Purpose**: No new project initialisation needed — existing Python/pytest/SQLAlchemy setup is reused. Phase 1 is a single documentation task.

- [ ] T001 Confirm feature branch `003-russian-language-support` is checked out and up to date with `main`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: DB schema change + core i18n module that ALL four user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Add `language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)` to `User` model in `src/glucotrack/models/user.py`; add `String` to SQLAlchemy imports
- [ ] T003 Add `SupportedLanguage` StrEnum (`EN = "en"`, `RU = "ru"`) to `src/glucotrack/models/user.py`; export from `src/glucotrack/models/__init__.py`
- [ ] T004 Add `update_language(telegram_user_id, language_code) -> User` and helper `effective_lang(user) -> str` (returns `"en"` for `None`) to `src/glucotrack/repositories/user_repository.py`
- [ ] T005 Create `src/glucotrack/bot/i18n.py` with `SUPPORTED: frozenset`, `DEFAULT_LANG = "en"`, `STRINGS: dict[str, dict[str, str]]` (skeleton with all ~20 keys, English values only), and `t(key, lang, **kwargs) -> str` helper that falls back to `DEFAULT_LANG`

**Checkpoint**: `User.language_code` column exists; `i18n.t()` is callable; repository can persist language preference.

---

## Phase 3: User Story 1 — Switch Language Preference (Priority: P1) 🎯 MVP

**Goal**: User sends `/language ru` or `/language en`; preference is persisted and all subsequent bot messages use that language.

**Independent Test**: Set language to Russian → send `/status` → verify Russian response text; set back to English → verify English. No AI analysis or Miro required.

> **TDD REQUIRED: Write tests first — confirm RED — then implement**

- [ ] T006 [P] [US1] Write failing unit tests for `t()` helper covering: key lookup, lang fallback to `"en"`, format kwargs, missing key raises `KeyError` — in `tests/unit/test_i18n.py`
- [ ] T007 [P] [US1] Write failing contract tests for `/language` command: valid code switches language, unsupported code returns error in current language, missing argument returns usage hint — in `tests/contract/test_language_command_contract.py`
- [ ] T008 [US1] Fill all Russian translations in `i18n.STRINGS` in `src/glucotrack/bot/i18n.py` — one entry per existing `fmt_*` function (welcome, photo_type_prompt, cgm_timing_prompt, food_ack, cgm_ack, activity_ack, session_status, analysis_queued, session_cancelled, disambiguation_prompt, insufficient_entries, analysis_result sections, cgm_unparseable, analysis_error, no_session, trend_insufficient, trend_coming_soon, generic_error, help, language_changed, language_error, language_usage)
- [ ] T009 [P] [US1] Add `lang: str = "en"` kwarg to every public `fmt_*` function in `src/glucotrack/bot/formatters.py`; call `t(key, lang, ...)` for all user-visible strings (keep `_escape` centralised in formatter functions)
- [ ] T010 [US1] Add `fmt_language_changed(lang_code, lang) -> str` and `fmt_language_error(unsupported_code, lang) -> str` and `fmt_language_usage(lang) -> str` to `src/glucotrack/bot/formatters.py` (new message types for `/language` command responses)
- [ ] T011 [US1] Implement `/language` command handler `handle_language_command` in `src/glucotrack/bot/handlers.py`: validate code against `SupportedLanguage`, call `user_repository.update_language()`, update `context.user_data["lang"]`, reply with `fmt_language_changed` or `fmt_language_error`; register the command in the application builder
- [ ] T012 [US1] Thread `lang` through all existing handlers in `src/glucotrack/bot/handlers.py`: at the top of each handler, resolve `lang = context.user_data.get("lang") or await _get_user_lang(user_id, db)` and pass to every `formatters.*` call; add `_get_user_lang(user_id, db) -> str` helper that caches result in `context.user_data["lang"]`
- [ ] T013 [US1] Write failing integration test for language persistence across sessions: set Russian → verify bot response in Russian → simulate new session → verify still Russian — in `tests/integration/test_language_flow.py`

**Checkpoint**: `/language ru` works; all bot messages arrive in Russian; preference survives restarts.

---

## Phase 4: User Story 2 — AI Analysis in Russian (Priority: P2)

**Goal**: When user's language is Russian, AI analysis delivered via Telegram is in Russian.

**Independent Test**: Set user language to Russian, run mock `analyse_session()` with `language="ru"`, verify the system prompt passed to Claude contains the Russian language instruction suffix.

> **TDD REQUIRED: Write tests first — confirm RED — then implement**

- [ ] T014 [P] [US2] Write failing unit test: `analyse_session(..., language="ru")` appends Russian language instruction to system prompt; `language="en"` leaves prompt unchanged — in `tests/unit/test_ai_service.py`
- [ ] T015 [US2] Add `_LANGUAGE_INSTRUCTIONS: dict[str, str] = {"ru": "..."}` dict to `src/glucotrack/services/ai_service.py` and add `language: str = "en"` parameter to `AIService.analyse_session()`; append suffix to `SESSION_ANALYSIS_SYSTEM_PROMPT` when `language != "en"`
- [ ] T016 [US2] Thread `language` from user preference through `AnalysisService.run_analysis()` in `src/glucotrack/services/analysis_service.py`: fetch user's `language_code` early in `run_analysis()` and pass it to `self._ai.analyse_session(..., language=lang)`; also pass `lang` to `formatters` calls for Telegram delivery messages
- [ ] T017 [P] [US2] Extend `tests/integration/test_language_flow.py` with test: Russian-language user completes session → `mock_ai.analyse_session` called with `language="ru"` (verify via call_args)

**Checkpoint**: `AIService.analyse_session(language="ru")` sends Russian-instructed prompt; `AnalysisService` propagates the user's language preference end-to-end.

---

## Phase 5: User Story 3 — Miro Board Card in Russian (Priority: P3)

**Goal**: Miro card section labels and analysis text for a Russian-preference user are in Russian.

**Independent Test**: Call `create_enhanced_session_card(analysis, session_images, lang="ru")` with respx mock; capture the `text` content POSTed to the sticky notes endpoint; verify it contains Russian section labels.

> **TDD REQUIRED: Write tests first — confirm RED — then implement**

- [ ] T018 [P] [US3] Write failing unit test: `_build_section_text("food", data, lang="ru")` returns Russian section label ("**Питание**" etc.); `lang="en"` returns English — in `tests/unit/test_miro_service.py`
- [ ] T019 [US3] Add Russian section labels to `i18n.STRINGS` in `src/glucotrack/bot/i18n.py` (keys: `miro_food_header`, `miro_activity_header`, `miro_glucose_header`, `miro_correlation_header`, `miro_recommendations_header` — English and Russian values)
- [ ] T020 [US3] Add `lang: str = "en"` parameter to `create_enhanced_session_card()` and `_build_section_text()` in `src/glucotrack/services/miro_service.py`; use `i18n.t()` for section header strings
- [ ] T021 [US3] Thread `lang` from `AnalysisService._create_miro_card_safe()` in `src/glucotrack/services/analysis_service.py`: pass `analysis.user_id`-resolved language to `self._miro.create_enhanced_session_card(..., lang=lang)`

**Checkpoint**: Miro sticky note `text` payload for Russian users contains Russian headers.

---

## Phase 6: User Story 4 — Trend Analysis in Russian (Priority: P4) ⏸ DEFERRED

**Status**: Deferred — trend analysis feature itself is not yet implemented (per spec assumptions).
**Action**: Skip this phase until the trend analysis feature exists. Language support for it will be added in the same PR as trend analysis.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T022 Run full test suite `pytest tests/ -v --tb=short` and verify coverage ≥ 80%; fix any failures
- [ ] T023 [P] Run `ruff check src/ tests/` and `black --check src/ tests/`; fix all issues
- [ ] T024 [P] Run `mypy src/`; resolve all type errors (especially `lang: str` annotations on formatters)
- [ ] T025 Update sandbox `MockMiroService.create_enhanced_session_card` signature to accept `lang` kwarg in `sandbox/mocks.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 2 (Foundational)**: Blocks ALL user story phases — `User.language_code`, `i18n.t()`, and `UserRepository.update_language()` are prerequisites for US1–US3
- **US1 (Phase 3)**: Depends on Phase 2 — language persistence and formatter `lang` kwarg needed
- **US2 (Phase 4)**: Depends on Phase 2 + US1 (handlers must thread `lang` before AI call can use it)
- **US3 (Phase 5)**: Depends on Phase 2 + US2 (Miro `lang` flows through `AnalysisService` which already threads it for AI)
- **US4 (Phase 6)**: Deferred — no dependency to track

### Within Each Phase

1. Write test → confirm RED
2. Implement → confirm GREEN
3. Commit (one logical change per commit)

### Parallel Opportunities

```bash
# Phase 2 — T002, T003, T004, T005 can run in parallel (different files):
T002: models/user.py
T003: models/user.py (same file as T002 — sequential)
T004: repositories/user_repository.py
T005: bot/i18n.py

# Phase 3 — T006 and T007 tests can be written in parallel:
T006: tests/unit/test_i18n.py
T007: tests/contract/test_language_command_contract.py

# Phase 4 — T014 test and Phase 5 T018 test can be written in parallel once Phase 3 is done:
T014: tests/unit/test_ai_service.py
T018: tests/unit/test_miro_service.py
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 2: Foundational
2. Complete Phase 3: US1 (`/language` command + formatter `lang` kwarg)
3. **STOP and VALIDATE**: `/language ru` works; all bot messages are in Russian; preference persists
4. This alone delivers the core value of the feature for Russian-speaking users

### Incremental Delivery

1. Phase 2 → Foundation ready
2. Phase 3 (US1) → Language switching works; bot speaks Russian ✅
3. Phase 4 (US2) → AI analysis in Russian ✅
4. Phase 5 (US3) → Miro card in Russian ✅
5. Phase 6 (US4) → Skip until trend analysis feature lands

---

## Notes

- Every `fmt_*` function gets `lang: str = "en"` — **keyword-only default** — so no existing call sites break
- `context.user_data["lang"]` acts as a per-user in-session cache; first access hits the DB, subsequent accesses use cached value
- `_escape()` in `formatters.py` is NOT translated — it's a MarkdownV2 utility; translated strings in `i18n.STRINGS` must already be MarkdownV2-correct
- The Russian language instruction appended to the AI prompt should be the last line of `system` — Claude follows end-of-prompt instructions most reliably
- US4 (trend analysis in Russian) is intentionally deferred — the trend analysis feature itself does not yet exist
