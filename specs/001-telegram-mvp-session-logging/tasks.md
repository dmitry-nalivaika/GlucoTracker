# Tasks: GlucoTrack Telegram MVP — Session Logging & AI Analysis

**Input**: Design documents from `specs/001-telegram-mvp-session-logging/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**TDD is mandatory** — every test task MUST be written and confirmed failing before its implementation task begins.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialisation, tooling, and directory structure.

- [x] T001 Create directory structure per plan.md: `src/glucotrack/{bot,domain,models,repositories,services,storage}`, `tests/{unit,integration,contract}`, `alembic/versions`, `docs/{developer,user,extension}`
- [x] T002 Create `pyproject.toml` with Python 3.11, all runtime deps (`python-telegram-bot==22.*`, `anthropic>=0.40`, `sqlalchemy[asyncio]>=2.0`, `aiosqlite`, `httpx`, `pydantic>=2`, `alembic`), dev deps (`pytest`, `pytest-asyncio`, `pytest-cov`, `respx`, `ruff`, `black`, `mypy`)
- [x] T003 [P] Configure `ruff`, `black`, `mypy` rules in `pyproject.toml` (line-length 100, Python 3.11 target, strict mypy)
- [x] T004 [P] Create `.env.example` with all env vars documented per `quickstart.md` (no real secrets)
- [x] T005 [P] Create `requirements.txt` (runtime) and `requirements-dev.txt` (dev extras) generated from `pyproject.toml`
- [x] T006 [P] Initialise Alembic: create `alembic/env.py` and `alembic/script.py.mako` configured to use `DATABASE_URL` from env

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required by ALL user stories. No story work begins until this phase is complete.

⚠️ CRITICAL: Complete this phase before any Phase 3+ work.

- [x] T007 Create `src/glucotrack/config.py` — pydantic `BaseSettings` class loading all env vars from `quickstart.md` env reference; validate required secrets present at startup
- [x] T008 [P] Create `src/glucotrack/models/base.py` — SQLAlchemy 2.0 `DeclarativeBase`, UUID helper type, UTC datetime helper
- [x] T009 Create `src/glucotrack/models/user.py` — `User` ORM model (see `data-model.md`: `users` table)
- [x] T010 Create `src/glucotrack/models/session.py` — `Session` ORM model with status enum `open|completed|analysed|expired` (see `data-model.md`: `sessions` table)
- [x] T011 Create `src/glucotrack/models/entries.py` — `FoodEntry`, `CGMEntry`, `ActivityEntry` ORM models (see `data-model.md`)
- [x] T012 Create `src/glucotrack/models/analysis.py` — `AIAnalysis` and `TrendAnalysis` ORM models (BOTH required from day one per spec Assumptions; see `data-model.md`)
- [x] T013 [P] Create `src/glucotrack/models/miro.py` — `MiroCard` ORM model with `source_type` enum `analysis|trend` (see `data-model.md`)
- [x] T014 Create `src/glucotrack/db.py` — async SQLAlchemy engine factory, async session factory, `init_db()` to create all tables; `python -m glucotrack.db init` CLI command
- [x] T015 Create `alembic/versions/001_initial_schema.py` — migration creating all 7 tables from `data-model.md` in correct FK order
- [x] T016 Create `src/glucotrack/storage/local_storage.py` — `StorageRepository` class: `save_file(user_id, session_id, filename, data) -> str` (returns relative path); enforces `/users/{user_id}/sessions/{session_id}/` path pattern (Constitution II)
- [x] T017 [P] Create `tests/conftest.py` — shared pytest fixtures: async in-memory SQLite DB (`test_db`), mock `AIService`, mock `MiroService`, mock `StorageRepository`, sample `User`, sample open `Session`
- [x] T018 [P] Create `src/glucotrack/__init__.py` and `src/glucotrack/__main__.py` — entry point running bot in polling mode; loads config, inits DB, starts PTB application
- [x] T019 [P] Write unit tests for `config.py` in `tests/unit/test_config.py` — missing required env vars raise `ValidationError`; all defaults load correctly
- [x] T020 [P] Write unit tests for `local_storage.py` in `tests/unit/test_storage.py` — correct path returned; file written to correct location; path isolation per user_id

**Checkpoint**: Foundation ready — all models, DB, storage exist. User story implementation can begin.

---

## Phase 3: User Story 1 — Log a Meal Session via Telegram (Priority: P1) 🎯 MVP

**Goal**: User can send food photos, CGM screenshots, and activity text to the bot. Bot groups them into a session, persists everything under `users/{user_id}/sessions/{session_id}/`, and confirms receipt within 2 seconds.

**Independent Test**: Send a food photo + CGM screenshot to the bot → type "Food photo" → type "CGM screenshot" → choose "1 hour after" → `/done` → bot confirms session complete. Verify rows in `sessions`, `food_entries`, `cgm_entries` tables all have matching `user_id`.

### Tests for User Story 1 ⚠️ Write FIRST — confirm FAIL before implementing

- [x] T021 [P] [US1] Unit test for session state machine in `tests/unit/test_session_domain.py` — `open→completed` transition requires ≥1 food + ≥1 CGM entry; `open→expired` transition; invalid transitions raise errors
- [x] T022 [P] [US1] Unit test for user domain in `tests/unit/test_user_domain.py` — `get_or_create_user(telegram_user_id)` creates on first call, returns existing on second call; `user_id` tagged on all returned objects
- [x] T023 [P] [US1] Unit test for `SessionRepository` in `tests/unit/test_repositories.py` — `get_open_session(user_id)` returns None when none exists; entry counts correct; all queries use `user_id` predicate; cross-user isolation (user A cannot see user B's session)
- [x] T024 [P] [US1] Integration test for full session logging flow in `tests/integration/test_session_flow.py` — open session, add food entry, add CGM entry, add activity entry, complete session, assert DB state and storage paths

### Implementation for User Story 1

- [x] T025 [P] [US1] Create `src/glucotrack/domain/user.py` — `get_or_create_user(session, telegram_user_id) -> User`; updates `last_seen_at` on each call; no query runs without `user_id`
- [x] T026 [US1] Create `src/glucotrack/domain/session.py` — `SessionStateMachine`: `can_complete(session) -> bool` (requires ≥1 food + ≥1 CGM); `transition(session, action)` with validation; idle gap detection logic
- [x] T027 [US1] Create `src/glucotrack/repositories/user_repository.py` — `UserRepository`: `get_by_telegram_id`, `create`, `update_last_seen`; all methods take `user_id`; parameterised ORM queries only
- [x] T028 [US1] Create `src/glucotrack/repositories/session_repository.py` — `SessionRepository`: `get_open_session(user_id)`, `create_session(user_id)`, `add_food_entry(user_id, session_id, ...)`, `add_cgm_entry(user_id, session_id, ...)`, `add_activity_entry(user_id, session_id, ...)`, `complete_session(user_id, session_id)`, `expire_session(user_id, session_id)`; ALL methods scope by `user_id`
- [x] T029 [US1] Create `src/glucotrack/services/session_service.py` — `SessionService`: orchestrates `UserRepository` + `SessionRepository` + `StorageRepository`; `handle_photo(user_id, file_data, entry_type, timing_label=None)`, `handle_activity(user_id, text)`, `complete_session(user_id) -> Session`; idle gap detection (FR-013); session auto-expiry logic (FR-012)
- [x] T030 [US1] Create `src/glucotrack/bot/formatters.py` — MarkdownV2 formatters for: acknowledgement messages, session status, disambiguation prompt, error messages; all user-facing strings defined here (no string literals in handlers)
- [x] T031 [US1] Create `src/glucotrack/bot/handlers.py` — Telegram handlers: `handle_start`, `handle_new_session`, `handle_photo` (with photo-type prompt), `handle_cgm_timing`, `handle_activity_text`, `handle_done`, `handle_cancel`, `handle_status`, `handle_disambiguate_session`; all handlers respond within 2s (SC-002); all use `SessionService`
- [x] T032 [US1] Create `src/glucotrack/bot/application.py` — PTB `Application` factory with `ConversationHandler` mapping all states from `contracts/telegram-handlers.md`; `JobQueue` configured for session expiry jobs

**Checkpoint**: US1 independently functional. Bot accepts inputs, persists them, confirms receipt within 2s. No AI analysis yet.

---

## Phase 4: User Story 2 — Receive AI Analysis of a Session (Priority: P2)

**Goal**: After `/done`, user receives a structured 4-section analysis (nutrition, glucose curve, correlation, recommendations) within 30 seconds. CGM parse failures handled gracefully with user guidance.

**Independent Test**: Complete a session (US1), trigger analysis with a test food photo + CGM screenshot, assert Telegram message contains all 4 sections, glucose values reference 70–140 mg/dL range. Test with a blurry CGM mock response — assert graceful degradation message.

### Tests for User Story 2 ⚠️ Write FIRST — confirm FAIL before implementing

- [x] T033 [P] [US2] Unit test for `AIService` in `tests/unit/test_ai_service.py` — correct Claude API request built (model, max_tokens, image blocks, system prompt); response parsed to expected schema; `cgm_parseable: false` handled (graceful path); rate limit enforced (>10 calls returns error); token budget enforced; API error triggers retry once then raises
- [x] T034 [P] [US2] Unit test for `AnalysisService` in `tests/unit/test_analysis_service.py` — session with no AI analysis triggers analysis call; result persisted to `ai_analyses` table; `AIAnalysis.user_id` matches `session.user_id`; `cgm_parse_error` path notifies user without failing session
- [x] T035 [P] [US2] Contract test for Claude API schema in `tests/contract/test_claude_api_schema.py` — validates request payload matches schema in `contracts/claude-api-schema.md`; validates response JSON parses to expected structure; validates required fields present
- [x] T036 [P] [US2] Integration test for analysis pipeline in `tests/integration/test_analysis_flow.py` — mock Claude client returns valid analysis JSON; assert `AIAnalysis` row created with correct `user_id`; assert formatted Telegram message contains all 4 sections

### Implementation for User Story 2

- [x] T037 [US2] Create `src/glucotrack/services/ai_service.py` — `AIService`: `analyse_session(session, food_entries, cgm_entries, activity_entries) -> dict`; builds Claude API request per `contracts/claude-api-schema.md`; parses JSON response; enforces rate limit (token bucket, 10 calls/user/day) and token budget (4000 tokens/session); handles `APIStatusError` with one retry; raises `AnalysisError` on persistent failure
- [x] T038 [US2] Create `src/glucotrack/repositories/analysis_repository.py` — `AnalysisRepository`: `save_analysis(user_id, session_id, analysis_data) -> AIAnalysis`; `get_analysis_by_session(user_id, session_id) -> Optional[AIAnalysis]`; all queries scope by `user_id`
- [x] T039 [US2] Create `src/glucotrack/services/analysis_service.py` — `AnalysisService`: orchestrates `AIService` + `AnalysisRepository`; `run_analysis(user_id, session_id)`; sends "Analysis in progress…" within 2s; delivers formatted result via `bot.send_message`; handles `cgm_parseable: false` per FR-011; handles timeout/failure per spec edge cases; fires Miro card creation after delivery (fire-and-forget)
- [x] T040 [US2] Add analysis result formatters to `src/glucotrack/bot/formatters.py` — `format_analysis_result(analysis: AIAnalysis) -> str` producing the 4-section MarkdownV2 message per `contracts/telegram-handlers.md`
- [x] T041 [US2] Wire analysis into `src/glucotrack/bot/handlers.py` — `handle_done` fires `AnalysisService.run_analysis` as asyncio background task after immediate acknowledgement

**Checkpoint**: US1 + US2 complete. Full session → analysis → Telegram delivery flow working. Miro not yet wired.

---

## Phase 5: User Story 3 — Visualise Session on Miro Board (Priority: P3)

**Goal**: After analysis is delivered to Telegram, a structured card automatically appears on the Miro board within 5 seconds. Miro failure never blocks Telegram delivery.

**Independent Test**: Complete US2 flow with mock Miro service; assert `miro_cards` row created with `status=created` and correct `user_id`. Test Miro API 500 error → assert Telegram delivery still succeeds and `miro_cards.status=failed`.

### Tests for User Story 3 ⚠️ Write FIRST — confirm FAIL before implementing

- [x] T042 [P] [US3] Unit test for `MiroService` in `tests/unit/test_miro_service.py` — correct POST body built per `contracts/miro-api-schema.md`; 201 response stores `miro_card_id`; 429 triggers retry with backoff; 5xx triggers retry up to 3×; 4xx sets `status=failed` with no retry; anonymised user ID in card title (never raw telegram_user_id)
- [x] T043 [P] [US3] Contract test for Miro API schema in `tests/contract/test_miro_api_schema.py` — validates POST request body matches `contracts/miro-api-schema.md`; validates `miro_card_id` extracted from 201 response
- [x] T044 [P] [US3] Integration test for Miro flow in `tests/integration/test_miro_flow.py` — mock Miro API (respx); after analysis delivered, `MiroCard` row exists with `status=created`; Miro 500 error → `status=failed`, Telegram delivery unaffected

### Implementation for User Story 3

- [x] T045 [US3] Create `src/glucotrack/services/miro_service.py` — `MiroService`: `create_session_card(analysis: AIAnalysis) -> str` (returns miro_card_id); builds card payload per `contracts/miro-api-schema.md`; anonymises user ID (short hash, never raw telegram_user_id); retry logic (429: Retry-After; 5xx: exponential backoff 1s/2s/4s, max 3 retries); `httpx.AsyncClient` for async HTTP
- [x] T046 [US3] Wire `MiroService` into `src/glucotrack/services/analysis_service.py` — after `bot.send_message` succeeds, fire `asyncio.create_task(miro_service.create_session_card(analysis))` as fire-and-forget; persist `MiroCard` record with outcome

**Checkpoint**: Full US1 + US2 + US3 flow complete. Session → analysis → Telegram + Miro card.

---

## Phase 6: User Story 4 — Trend Analysis Data Readiness (Priority: P4 — deferred)

**Goal**: Data model supports trend analysis queries from day one. `/trend` command exists as a stub. Full trend analysis deferred to next sprint but data infrastructure is in place.

**Independent Test**: Seed 5 completed+analysed sessions for a test user; execute `AnalysisRepository.get_analysed_sessions_for_trend(user_id, min_count=3)`; assert returns correct sessions with `user_id` isolation. Send `/trend` to bot; assert response tells user how many sessions they have.

### Tests for User Story 4 ⚠️ Write FIRST — confirm FAIL before implementing

- [x] T047 [P] [US4] Integration test for trend data readiness in `tests/integration/test_trend_flow.py` — seed 5 analysed sessions for user A and 3 for user B; `get_analysed_sessions_for_trend(user_id=A)` returns exactly 5 sessions all with `user_id=A`; user B's sessions not included; with < 3 sessions, service raises `InsufficientDataError` with session count

### Implementation for User Story 4

- [x] T048 [US4] Add `get_analysed_sessions_for_trend(user_id, min_count=3) -> list[Session]` to `src/glucotrack/repositories/session_repository.py` — returns sessions with `status=analysed` for `user_id`; raises `InsufficientDataError(current_count)` if count < `min_count` (FR-015); query scoped by `user_id`
- [x] T049 [US4] Add `/trend` command stub to `src/glucotrack/bot/handlers.py` — `handle_trend`: calls `SessionRepository.get_analysed_sessions_for_trend`; if `InsufficientDataError`, replies with "You need {min} analysed sessions for trend analysis. You have {n}." (FR-015); if sufficient, replies with "Trend analysis coming soon — you have {n} sessions ready."

**Checkpoint**: Trend data model verified. `/trend` stub functional. Full trend analysis ready to implement in next sprint.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Session lifecycle automation, documentation, final validation.

- [x] T050 [P] Unit test for `formatters.py` in `tests/unit/test_formatters.py` — all formatter functions return valid MarkdownV2; analysis result contains all 4 sections; error messages are human-readable (no stack traces); trend insufficient-data message includes session count
- [x] T051 [P] Unit test for `session_service.py` idle + expiry logic in `tests/unit/test_session_service.py` — idle gap > 30 min triggers disambiguation prompt; disambiguation timeout 2h auto-closes session (FR-013); session idle > 24h triggers expiry (FR-012)
- [x] T052 Add session auto-expiry `JobQueue` job to `src/glucotrack/services/session_service.py` — scheduled job (runs every 30 min) that queries open sessions with `last_input_at` older than `SESSION_IDLE_EXPIRY_HOURS`, marks them `expired`, enqueues for analysis if they have ≥1 food + ≥1 CGM entry (FR-012)
- [x] T053 [P] Create `docs/developer/architecture.md` — component diagram, layer descriptions, data flow from Telegram → domain → DB → Claude → Miro
- [x] T054 [P] Create `docs/developer/setup.md` — mirrors `quickstart.md`; local dev prerequisites, install steps, env config, run commands
- [x] T055 [P] Create `docs/user/getting-started.md` — end-to-end guide: start session, log food, add CGM, log activity, complete session, read analysis, check Miro board
- [x] T056 [P] Create `docs/extension/adding-input-channel.md` — how to add a new input channel replacing/alongside Telegram bot (interface/adapter pattern)
- [x] T057 Run full test suite: `pytest tests/ -v --cov=src/glucotrack --cov-report=term-missing --cov-fail-under=80` — fix any failures; ensure coverage ≥ 80%
- [x] T058 Run lint + format + type checks: `ruff check src/ tests/ && black --check src/ tests/ && mypy src/` — fix all reported issues
- [x] T059 [P] Run security scan: `bandit -r src/ -ll` — resolve any HIGH severity findings (Constitution CI pipeline Stage 6)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 — tests first, then implementation
- **Phase 4 (US2)**: Depends on Phase 3 completion — tests first, then implementation
- **Phase 5 (US3)**: Depends on Phase 4 completion — tests first, then implementation
- **Phase 6 (US4)**: Depends on Phase 2 (data model); can run in parallel with Phase 4/5 after models exist
- **Phase 7 (Polish)**: Depends on all desired stories complete

### Within Each User Story

```
Tests → (confirm FAIL) → Models → Repositories → Services → Handlers → (confirm PASS)
```

### Parallel Opportunities

- All `[P]` tasks within a phase can run concurrently (different files, no dependencies)
- Phase 6 (US4 stubs) can begin after T015 (initial schema) with T048 as a repository extension

---

## Parallel Execution Examples

### Phase 2 — Run Together

```
Task T008: src/glucotrack/models/base.py
Task T013: src/glucotrack/models/miro.py
Task T016: src/glucotrack/storage/local_storage.py
Task T017: tests/conftest.py
Task T019: tests/unit/test_config.py
Task T020: tests/unit/test_storage.py
```

### Phase 3 (US1) — Tests Together, Then Implementation

```
# Launch tests first (all [P]):
Task T021: tests/unit/test_session_domain.py
Task T022: tests/unit/test_user_domain.py
Task T023: tests/unit/test_repositories.py
Task T024: tests/integration/test_session_flow.py

# After confirming FAIL, launch models together [P]:
Task T025: src/glucotrack/domain/user.py
Task T026: src/glucotrack/domain/session.py (depends on T025)
```

### Phase 4 (US2) — Tests Together

```
Task T033: tests/unit/test_ai_service.py
Task T034: tests/unit/test_analysis_service.py
Task T035: tests/contract/test_claude_api_schema.py
Task T036: tests/integration/test_analysis_flow.py
```

---

## Implementation Strategy

### MVP Scope (P1 only — US1)

1. Complete Phase 1 + Phase 2 (Foundation)
2. Complete Phase 3 (US1 — Session Logging)
3. **VALIDATE**: Full session flow works end-to-end in Telegram, data isolated per user
4. Ready for demo: users can log sessions, data persisted correctly

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready
2. Phase 3 → US1 MVP: session logging works ✓
3. Phase 4 → US2: AI analysis delivered in Telegram ✓
4. Phase 5 → US3: Miro board populated ✓
5. Phase 6 → US4 data ready: trend analysis implementable next sprint ✓
6. Phase 7 → Quality gates met, docs complete, PR ready ✓

---

## Notes

- `[P]` = different files, no intra-phase dependencies — can run concurrently
- `[US#]` = maps task to user story for traceability
- TDD is mandatory: test tasks have no `[P]` relationship with their implementation tasks — tests MUST fail before implementation begins
- All repository methods MUST include `user_id` parameter — no exceptions (Constitution II)
- All file writes MUST go through `StorageRepository` — no direct `open()` calls outside it (Constitution II)
- Secrets MUST come from `config.py` only — no `os.environ` direct calls in handlers or services
