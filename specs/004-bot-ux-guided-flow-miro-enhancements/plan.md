# Implementation Plan: 004 — Bot UX: Guided Flow, Action Keyboard, Status Messages & Miro Card Enhancements

**Branch**: `004-bot-ux-guided-flow-miro-enhancements`
**Date**: 2026-04-24
**Spec**: `specs/004-bot-ux-guided-flow-miro-enhancements/spec.md`
**Input**: Feature specification from `/specs/004-bot-ux-guided-flow-miro-enhancements/spec.md`

---

## Summary

Three coordinated UX improvements: (1) guided step-by-step bot messages + persistent
action keyboard so users always know what to do next; (2) online/offline broadcast
requiring a new `chat_id` column in the `users` table; (3) Miro card enrichment with
RAG glucose badge, AI-generated executive summary, and single-row photo layout.

All changes are additive — no breaking refactors. The AI prompt gains two new fields;
the Miro frame layout gains one new sticky note row.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: python-telegram-bot 22.x, httpx, SQLAlchemy asyncio, Alembic, anthropic SDK
**Storage**: SQLite (dev) → Azure SQL (prod); files via LocalStorageRepository
**Testing**: pytest + pytest-asyncio, respx (httpx mocking), MagicMock for PTB objects
**Target Platform**: Linux server / Azure Container Apps
**Project Type**: Telegram bot service + Miro integration
**Performance Goals**: Bot ack < 2 s (SC-002); Miro card < 5 s
**Constraints**: $50/month hard cap (Constitution VII); no raw stack traces to users
**Scale/Scope**: Single-user MVP → multi-user production

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| No direct commits to `main` | ✅ PASS | Feature branch created |
| Every DB query scoped by `user_id` | ✅ PASS | `chat_id` stored per-user; broadcast query filters `chat_id IS NOT NULL` |
| File paths follow `/users/{uid}/sessions/{sid}/` | ✅ PASS | No new file storage |
| No raw stack traces to users | ✅ PASS | All errors use formatters |
| No hardcoded secrets | ✅ PASS | No new credentials |
| Constitution VII cost guard | ✅ PASS | No new Claude calls; executive_summary piggybacks existing call; no new Azure services |
| TDD mandatory (tests before implementation) | ✅ PASS | Enforced per task |
| No features outside spec | ✅ PASS | Scope bounded to US1–US3 |

**All gates pass. Proceeding to Phase 0.**

---

## Project Structure

### Documentation (this feature)

```text
specs/004-bot-ux-guided-flow-miro-enhancements/
├── plan.md              ← this file
├── spec.md              ← feature specification
├── research.md          ← Phase 0 decisions
├── data-model.md        ← Phase 1 schema changes
├── contracts/           ← updated AI prompt contract
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code

```text
src/glucotrack/
├── bot/
│   ├── handlers.py        ← guided acks, action keyboard, chat_id storage
│   ├── application.py     ← online broadcast post_init hook
│   ├── formatters.py      ← new fmt_guided_* functions
│   └── i18n.py            ← new strings (guided prompts, online/offline, miro)
├── models/
│   └── user.py            ← add chat_id field
├── repositories/
│   └── user_repository.py ← update_chat_id(), get_all_with_chat_id()
└── services/
    ├── ai_service.py      ← extend SESSION_ANALYSIS_SYSTEM_PROMPT
    └── miro_service.py    ← RAG badge, executive summary section, single-row photos

alembic/versions/004_add_chat_id.py   ← new migration

tests/
├── unit/
│   ├── test_formatters.py    ← guided prompt formatters
│   ├── test_miro_service.py  ← RAG badge, exec summary, single-row photos
│   └── test_user_repository.py ← update_chat_id, get_all_with_chat_id
├── integration/
│   └── test_bot_status.py    ← online broadcast (mocked PTB)
└── contract/
    └── test_ai_contract.py   ← updated prompt contract (new fields)
```

**Structure Decision**: Single-project layout (existing). All changes in existing
modules; one new migration; no new top-level packages.

---

## Complexity Tracking

No constitution violations. No extra complexity justified.
