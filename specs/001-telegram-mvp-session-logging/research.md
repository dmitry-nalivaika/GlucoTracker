# Research: GlucoTrack Telegram MVP — Session Logging & AI Analysis

**Date**: 2026-04-17 | **Feature**: 001-telegram-mvp-session-logging

---

## Decision 1: Python Version

**Decision**: Python 3.11
**Rationale**: LTS support, significant performance improvements over 3.10 (15–60% faster), full async support, excellent Azure App Service support. `python-telegram-bot` v22 and `anthropic` SDK are both tested against 3.11+.
**Alternatives considered**: 3.12 (minor instabilities in some async libraries as of 2026-Q1), 3.10 (no meaningful advantage over 3.11).

---

## Decision 2: Telegram Bot Library

**Decision**: `python-telegram-bot` v22
**Rationale**: Full asyncio since v20; built-in `ConversationHandler` maps directly to the session-based glucose logging workflow (multi-step: food photo → CGM screenshot(s) → activity → complete). Built-in `JobQueue` enables session auto-expiry (FR-012, FR-013). Largest English-speaking community (29k GitHub stars). Clean Azure App Service/Container Apps deployment — no event loop conflicts unlike aiogram's aiohttp dependency.
**Alternatives considered**: `aiogram` v3 (more powerful FSM, but steeper learning curve, aiohttp conflicts with Azure Functions worker model, smaller community).

---

## Decision 3: Storage — Relational Data

**Decision**: SQLite via SQLAlchemy 2.0 ORM for local dev/MVP; schema designed for Azure SQL migration
**Rationale**: Zero-configuration for local dev; SQLAlchemy 2.0's async engine + repository pattern means the storage driver is fully abstracted (Constitution III). Migration to Azure SQL Database (Basic tier, ~$5/month) requires only a connection string change. All queries parameterised via ORM (Constitution V, SQL injection prevention). UUID primary keys for all entities (safe for future distributed storage).
**Alternatives considered**: Azure SQL from day one (adds cost and infra overhead before MVP proves value), CosmosDB (NoSQL doesn't fit relational session/entry model), raw SQLite without ORM (loses migration path and parameterisation guarantees).

---

## Decision 4: Storage — File Storage

**Decision**: Local filesystem at `./data/users/{user_id}/sessions/{session_id}/` for MVP; abstracted behind `StorageRepository` interface for Azure Blob migration
**Rationale**: Follows Constitution II path pattern exactly. `StorageRepository` interface isolates domain code from storage driver (Constitution III). Azure Blob Storage (LRS, ~$0.02/GB/month) requires only a driver swap behind the interface.
**Alternatives considered**: Azure Blob from day one (adds SDK, auth, and cost complexity before MVP validates the workflow).

---

## Decision 5: Claude API Integration

**Decision**: `anthropic` SDK v0.40+ with vision support
**Rationale**: Official Anthropic SDK; supports `messages` endpoint with image content blocks for food photo and CGM screenshot analysis. `claude-3-5-sonnet-20241022` is the target model — best multimodal analysis at ~$3/M input tokens. All calls go through a dedicated `AIService` class (Constitution III isolation rule). Per-user rate limiting and per-session token budget enforced in `AIService` (Constitution VII).
**Alternatives considered**: Direct `httpx` calls to Anthropic API (no benefit over SDK, more error-prone).

---

## Decision 6: Miro Integration

**Decision**: `httpx` async client against Miro REST API v2
**Rationale**: Miro REST API v2 POST `/boards/{board_id}/cards` creates structured cards with `title`, `description`, and `url`. Developer access token (non-expiring) is sufficient for a single-board MVP. `httpx` is already a common async HTTP dependency; no Miro SDK needed. Miro failure is isolated in `MiroService` — bot continues delivery regardless (FR-009, SC-004).
**Alternatives considered**: Miro Python SDK (unofficial, unmaintained), `requests` (sync, blocks the event loop).

---

## Decision 7: Async Analysis Pattern

**Decision**: `asyncio` background tasks via Python `asyncio.create_task()` within python-telegram-bot's async handler context
**Rationale**: Analysis (Claude API call) can take up to 30 seconds (SC-003). Bot sends "Analysis in progress…" acknowledgement immediately (within 2s, SC-002) then fires the analysis as a background task. When complete, uses `context.bot.send_message()` to deliver the result. No external queue needed for MVP — asyncio tasks are sufficient for the expected volume (50 sessions/day max per SC-007).
**Alternatives considered**: Celery + Redis (operational overhead unjustified for MVP volume), Azure Service Bus (cost and complexity).

---

## Decision 8: Session Grouping Logic

**Decision**: Time-window based with 30-minute idle threshold (per FR-013)
**Rationale**: FR-013 explicitly specifies: if gap > 30 minutes (configurable), prompt the user to continue or start fresh. 2-hour no-response auto-closes existing session and queues for analysis. Implemented via `JobQueue` in python-telegram-bot scheduling a check task on each incoming message.
**Session expiry (FR-012)**: Abandoned open sessions auto-expire after 24 hours (configurable `SESSION_IDLE_EXPIRY_HOURS`).

---

## Decision 9: Rate Limiting

**Decision**: In-memory token-bucket per `user_id`, implemented in `AIService`
**Rationale**: Simple and sufficient for MVP. Limits: max 10 analysis calls/user/day, max 4,000 output tokens/session. Prevents runaway costs (Constitution VII). Will migrate to Redis-backed rate limiting when multi-instance deployment is needed.
**Alternatives considered**: Redis from day one (overkill for single-instance MVP).

---

## Decision 10: Testing Framework

**Decision**: `pytest` + `pytest-asyncio` + `pytest-cov` + `respx` (mock httpx) + `unittest.mock`
**Rationale**: Standard Python async test stack. `respx` provides clean async HTTP mocking for Miro and Claude API calls without real network calls. Coverage enforced at 80% minimum (Constitution V). `ruff` + `black` + `mypy` for code quality (Constitution V).

---

## Resolved TODOs

- **TODO(SESSION_GROUPING)**: Resolved → 30-minute idle threshold, time-window based (FR-013).
- **TODO(TELEGRAM_IDENTITY)**: Resolved for MVP → Telegram user ID is the user identity, no separate auth.
- **TODO(STORAGE_ENGINE)**: Deferred but designed for → SQLite now, Azure SQL migration via SQLAlchemy driver swap.
- **TODO(AZURE_SERVICES)**: Deferred but target is → Azure App Service (Basic B1, ~$13/month) or Azure Container Apps.
