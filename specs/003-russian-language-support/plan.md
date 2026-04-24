# Implementation Plan: Russian Language Support

**Branch**: `003-russian-language-support` | **Date**: 2026-04-24 | **Spec**: `specs/003-russian-language-support/spec.md`
**Input**: Feature specification from `specs/003-russian-language-support/spec.md`

## Summary

Add user-selectable Russian/English language support across all GlucoTrack output layers.
A `language_code` column is added to the `User` model; a `bot/i18n.py` translation catalogue
holds all user-facing strings in both languages; all formatter functions gain a `lang` kwarg;
the AI system prompt gets a language instruction suffix; and the Miro card label strings are
localised. The `/language <code>` bot command stores and immediately applies the preference.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: python-telegram-bot 22.x, SQLAlchemy asyncio, aiosqlite, anthropic SDK
**Storage**: SQLite via aiosqlite (`language_code VARCHAR(10) NULL` column on `users` table)
**Testing**: pytest + pytest-asyncio, respx (httpx mocking), in-memory SQLite test fixtures
**Target Platform**: Linux server (Telegram bot process)
**Project Type**: Telegram bot + background analysis service
**Performance Goals**: Bot acknowledgement < 2 seconds (Constitution VI); language lookup adds ~1ms DB round-trip, cached in `context.user_data`
**Constraints**: No new pip dependencies; must pass `ruff` + `black` + `mypy --strict`
**Scale/Scope**: Per-user preference; 2 languages initially; architecture extensible (FR-009)

## Constitution Check

### Gate I — Multi-User Isolation (Constitution II) ✅

- `language_code` stored per user, always scoped by `user_id`
- Every DB query that reads/writes `language_code` uses `telegram_user_id` as predicate
- `context.user_data["lang"]` cache is per-Telegram-user (framework isolation)
- No global or shared language state

### Gate II — Feature-Based Delivery (Constitution IV) ✅

- Feature branch: `003-russian-language-support` ✓
- Spec exists: `specs/003-russian-language-support/spec.md` ✓
- This plan + Constitution Check completed before any code written ✓
- PR will be opened only when all quality gates pass ✓

### Gate III — Code Quality (Constitution V) ✅

- TDD: every task has test-first requirement
- Coverage target: ≥ 80% on new code
- `ruff` + `black` + `mypy --strict` must pass
- No hardcoded secrets; `language_code` is not sensitive data
- All user input (`/language <code>`) validated at system boundary (handler)

### Gate IV — Cost Management (Constitution VII) ✅

- Language instruction appended to AI prompt: +~15 tokens per analysis call
- No new Azure services; no new API dependencies
- Well within $50/month cap

**Constitution Check result: PASS — no violations to justify**

## Project Structure

### Documentation (this feature)

```text
specs/003-russian-language-support/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── language_command.md
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code Changes

```text
src/glucotrack/
├── bot/
│   ├── formatters.py           ← add lang= kwarg to all ~20 public functions
│   ├── handlers.py             ← add /language handler; thread lang through all calls
│   └── i18n.py                 ← NEW: translation catalogue + t() helper
├── models/
│   └── user.py                 ← add language_code column
├── repositories/
│   └── user_repository.py      ← add update_language() method
└── services/
    ├── ai_service.py           ← add language= param to analyse_session()
    ├── analysis_service.py     ← thread language from user through to AI call
    └── miro_service.py         ← add lang= to section label strings

tests/
├── unit/
│   ├── test_i18n.py            ← NEW: catalogue coverage
│   ├── test_formatters.py      ← extend with lang="ru" cases
│   └── test_language_handler.py← NEW: /language command handler
├── integration/
│   └── test_language_flow.py   ← NEW: set language → complete session → verify
└── contract/
    └── test_language_command_contract.py  ← NEW: /language command contract
```

**Structure Decision**: Single project layout (existing). New files: `bot/i18n.py` and test
files only. All other changes are additions to existing files.

## Complexity Tracking

No Constitution violations. No complexity justification required.
