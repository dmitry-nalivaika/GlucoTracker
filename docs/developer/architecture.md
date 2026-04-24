# GlucoTrack Architecture

## Component Diagram

```
Telegram User
     │
     ▼
┌─────────────────────────────────────────┐
│  PTB Application (bot/application.py)   │
│  ConversationHandler routes             │
└────────────────┬────────────────────────┘
                 │ calls
                 ▼
┌─────────────────────────────────────────┐
│  Telegram Handlers (bot/handlers.py)    │
│  handle_photo, handle_activity,         │
│  handle_done, handle_trend, …           │
└──────┬────────────┬──────────────┬──────┘
       │            │              │
       ▼            ▼              ▼
┌───────────┐ ┌──────────────┐ ┌──────────────────┐
│ Session   │ │ Analysis     │ │ Session          │
│ Service   │ │ Service      │ │ Repository       │
│           │ │              │ │ (trend query)    │
└───┬───────┘ └──────┬───────┘ └──────────────────┘
    │                │
    │          ┌─────┴──────┐
    │          │            │
    ▼          ▼            ▼
┌────────┐ ┌─────────┐ ┌────────────┐
│  DB    │ │   AI    │ │   Miro     │
│SQLite  │ │ Service │ │  Service   │
│(async) │ │(Claude) │ │(REST API)  │
└────────┘ └─────────┘ └────────────┘
```

## Layers

### Input Channel: Telegram Bot (`bot/`)
- `application.py` — PTB `Application` factory; wires `ConversationHandler`, `JobQueue`
- `handlers.py` — one async handler per user action; delegates to services immediately; never contains business logic
  - **Session action keyboard** (`_session_action_keyboard`): `ReplyKeyboardMarkup` with `/done`, `/cancel`, `/status`, `/settings` — shown whenever a session is open or an entry is acknowledged
  - **Flat photo classification keyboard** (`_photo_type_keyboard`): single-tap `InlineKeyboardMarkup` showing Food + 4 CGM timing options + Not sure; `flat:*` callbacks route directly to `_save_cgm` (no second step)
  - **Settings panel** (`handle_settings` / `handle_language_setting_callback`): `/settings` shows an inline language picker; `lang_set:*` callbacks are validated against `SupportedLanguage` before any DB write
  - **Post-session keyboard** (`_post_session_keyboard`): `ReplyKeyboardMarkup` with `/new`, `/trend`, `/settings` — sent with every analysis result/error message so the user always has navigation buttons
- `formatters.py` — all user-facing string templates (MarkdownV2); no string literals in handlers

### Domain (`domain/`)
- `user.py` — `get_or_create_user(session, telegram_user_id)`: idempotent user lookup/create
- `session.py` — `SessionStateMachine`: enforces `open → completed → analysed / open → expired` transitions; validates completion requires ≥1 food + ≥1 CGM entry

### Services (`services/`)
- `session_service.py` — session lifecycle orchestration: idle gap detection (FR-013), session auto-expiry (FR-012), entry persistence via repository
- `ai_service.py` — Claude API integration: builds vision requests, parses JSON response, enforces per-user rate limit (10 calls/day) and token budget (4000/session)
- `analysis_service.py` — analysis pipeline: calls `AIService`, persists `AIAnalysis`, delivers Telegram message, fires Miro card creation (fire-and-forget)
- `miro_service.py` — Miro REST API integration: creates session cards with anonymised user IDs, exponential backoff retries for 5xx/429

### Repositories (`repositories/`)
- All methods require `user_id` — no query runs without user context (Constitution II)
- `session_repository.py` — sessions, food/CGM/activity entries, completion/expiry transitions
- `analysis_repository.py` — AI analysis records, trend data queries
- `user_repository.py` — user lookup and last-seen updates

### Models (`models/`)
SQLAlchemy 2.0 ORM mapped classes — 7 tables: `users`, `sessions`, `food_entries`, `cgm_entries`, `activity_entries`, `ai_analyses`, `miro_cards`

### Storage (`storage/`)
- `local_storage.py` — `StorageRepository`: all file writes go through this; enforces path pattern `/users/{user_id}/sessions/{session_id}/filename`; no direct `open()` calls in services

## Data Flow: Session → Analysis → Miro

```
1. User sends food photo
   Telegram → handle_photo → SessionService.handle_photo()
   → StorageRepository.save_file() → /users/{id}/sessions/{sid}/food_xxx.jpg
   → SessionRepository.add_food_entry()
   → Bot replies "Food photo saved ✓" within 2s

2. User sends CGM screenshot → bot shows flat classification keyboard
   Telegram → handle_photo → bot sends InlineKeyboardMarkup with 6 options:
     🍽️ Food photo | 📈 CGM · before | 📈 CGM · right after |
     📈 CGM · 1h after | 📈 CGM · 2h after | 🤷 Not sure
   User taps one CGM option (flat:* callback) →
   handle_photo_type_callback → SessionService.handle_photo(entry_type='cgm')
   → StorageRepository.save_file() + SessionRepository.add_cgm_entry()

3. User sends /done
   Telegram → handle_done → SessionService.complete_session()
   → SessionStateMachine.validate_completion() (needs ≥1 food + ≥1 CGM)
   → SessionRepository.complete_session() → status = COMPLETED
   → Bot sends "Analysis in progress…" immediately

4. Background: AI analysis
   AnalysisService.run_analysis()
   → AIService.analyse_session() → Anthropic API (Claude vision)
   → AnalysisRepository.save_analysis()
   → SessionRepository.mark_analysed() → status = ANALYSED
   → Bot.send_message() → 4-section analysis to user

5. Background: Miro card (fire-and-forget, FR-009)
   asyncio.create_task(_create_miro_card_safe())
   → MiroService.create_session_card() → POST /boards/{id}/cards
   Failure here NEVER blocks Telegram delivery
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| All DB queries include `user_id` | Multi-tenant safety; prevents cross-user data leaks (Constitution II) |
| Files stored at `/users/{uid}/sessions/{sid}/` | Same isolation guarantee for binary data |
| Miro card creation is fire-and-forget | Miro outage must not block user receiving their analysis (FR-009) |
| MiroCard DB record persisted before async task | Avoids DB session lifecycle race between main flow and background task |
| AI service isolated behind `AIService` | No domain code calls Claude directly; easy to swap or mock (Constitution III) |
| StrEnum for status fields | Python 3.11+; serialises cleanly to/from DB strings |
