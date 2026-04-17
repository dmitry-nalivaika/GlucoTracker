# Data Model: GlucoTrack Telegram MVP

**Feature**: 001-telegram-mvp-session-logging | **Date**: 2026-04-17

All entities use UUID primary keys. All queries MUST include `user_id` predicate (Constitution II).
All timestamps stored as UTC datetime.

---

## Entity Diagram

```
User (1) ──── (many) Session
Session (1) ── (many) FoodEntry
Session (1) ── (many) CGMEntry
Session (1) ── (many) ActivityEntry
Session (1) ── (0..1) AIAnalysis
AIAnalysis (1) ── (0..1) MiroCard
User (1) ──── (many) TrendAnalysis
TrendAnalysis (1) ── (0..1) MiroCard
```

---

## Table: `users`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `telegram_user_id` | BIGINT | PRIMARY KEY | Telegram user ID — immutable identity |
| `created_at` | DATETIME | NOT NULL | UTC timestamp of first contact |
| `last_seen_at` | DATETIME | NOT NULL | UTC timestamp of most recent message |

**Notes**: User is created automatically on first Telegram interaction (FR-002). No password or email in MVP.

---

## Table: `sessions`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Session identifier |
| `user_id` | BIGINT | NOT NULL, FK → users | Owner; ALL queries MUST filter on this |
| `status` | VARCHAR(20) | NOT NULL | One of: `open`, `completed`, `analysed`, `expired` |
| `created_at` | DATETIME | NOT NULL | UTC timestamp when session opened |
| `last_input_at` | DATETIME | NOT NULL | UTC timestamp of last received input (for idle detection) |
| `completed_at` | DATETIME | nullable | UTC timestamp when user signalled completion |
| `expired_at` | DATETIME | nullable | UTC timestamp of auto-expiry |

**Status transitions**:
```
open → completed  (user signals /done)
open → expired    (idle > SESSION_IDLE_EXPIRY_HOURS, default 24h)
completed → analysed  (AI analysis delivered)
```

**Indexes**: `(user_id, status)` — for finding open sessions per user.

---

## Table: `food_entries`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Entry identifier |
| `session_id` | UUID | NOT NULL, FK → sessions | Parent session |
| `user_id` | BIGINT | NOT NULL, FK → users | Owner (denormalised for query scoping) |
| `file_path` | TEXT | NOT NULL | Relative path: `users/{user_id}/sessions/{session_id}/food_{id}.jpg` |
| `telegram_file_id` | TEXT | NOT NULL | Telegram file_id for original download |
| `description` | TEXT | nullable | Optional caption provided by user |
| `created_at` | DATETIME | NOT NULL | UTC timestamp |

---

## Table: `cgm_entries`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Entry identifier |
| `session_id` | UUID | NOT NULL, FK → sessions | Parent session |
| `user_id` | BIGINT | NOT NULL, FK → users | Owner |
| `file_path` | TEXT | NOT NULL | Relative path: `users/{user_id}/sessions/{session_id}/cgm_{id}.jpg` |
| `telegram_file_id` | TEXT | NOT NULL | Telegram file_id |
| `timing_label` | TEXT | NOT NULL | User-provided label e.g. "before eating", "1 hour after" |
| `created_at` | DATETIME | NOT NULL | UTC timestamp |

**Validation**: `timing_label` must be non-empty string, max 100 chars.

---

## Table: `activity_entries`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Entry identifier |
| `session_id` | UUID | NOT NULL, FK → sessions | Parent session |
| `user_id` | BIGINT | NOT NULL, FK → users | Owner |
| `description` | TEXT | NOT NULL | Free-text activity description |
| `created_at` | DATETIME | NOT NULL | UTC timestamp |

**Validation**: `description` must be non-empty, max 500 chars.

---

## Table: `ai_analyses`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Analysis identifier |
| `session_id` | UUID | NOT NULL, UNIQUE, FK → sessions | Source session (one-to-one) |
| `user_id` | BIGINT | NOT NULL, FK → users | Owner |
| `nutrition_json` | TEXT | NOT NULL | JSON: `{carbs_g, proteins_g, fats_g, gi_estimate, notes}` |
| `glucose_curve_json` | TEXT | NOT NULL | JSON: `[{timing_label, estimated_value_mg_dl, in_range}]` |
| `correlation_json` | TEXT | NOT NULL | JSON: `{spikes: [...], dips: [...], stable_zones: [...], summary}` |
| `recommendations_json` | TEXT | NOT NULL | JSON: `[{priority, text}]` |
| `within_target_notes` | TEXT | nullable | Free-text summary of 70–140 mg/dL compliance |
| `raw_response` | TEXT | NOT NULL | Full raw Claude API response (for debugging/re-analysis) |
| `created_at` | DATETIME | NOT NULL | UTC timestamp |

**Notes**: All JSON columns stored as TEXT (SQLite), as JSONB (PostgreSQL/Azure SQL migration).

---

## Table: `trend_analyses`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Analysis identifier |
| `user_id` | BIGINT | NOT NULL, FK → users | Owner |
| `session_count` | INT | NOT NULL | Number of sessions included |
| `period_start` | DATETIME | NOT NULL | Earliest session UTC timestamp in this trend |
| `period_end` | DATETIME | NOT NULL | Latest session UTC timestamp in this trend |
| `session_ids_json` | TEXT | NOT NULL | JSON array of session UUIDs included |
| `patterns_json` | TEXT | NOT NULL | JSON: `{stable: [...], spikes: [...], dips: [...]}` |
| `recommendations_json` | TEXT | NOT NULL | JSON: `[{priority, text}]` |
| `raw_response` | TEXT | NOT NULL | Full raw Claude API response |
| `created_at` | DATETIME | NOT NULL | UTC timestamp |

**Constraint**: `session_count >= 3` enforced at service layer (FR-015).

---

## Table: `miro_cards`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Card record identifier |
| `user_id` | BIGINT | NOT NULL, FK → users | Owner (anonymised identifier used on board) |
| `source_type` | VARCHAR(10) | NOT NULL | `analysis` or `trend` |
| `source_id` | UUID | NOT NULL | FK to `ai_analyses.id` or `trend_analyses.id` |
| `miro_board_id` | TEXT | NOT NULL | Board ID from config |
| `miro_card_id` | TEXT | nullable | Miro-assigned card ID (null until created) |
| `status` | VARCHAR(10) | NOT NULL | `pending`, `created`, `failed` |
| `retry_count` | INT | NOT NULL DEFAULT 0 | Number of creation attempts |
| `created_at` | DATETIME | NOT NULL | UTC timestamp |
| `updated_at` | DATETIME | NOT NULL | UTC timestamp of last status change |

---

## Validation Rules (System Boundaries)

All validation enforced at the Telegram handler layer before any data reaches services:

| Input | Validation Rule |
|---|---|
| Photo (food/CGM) | Must be Telegram `PhotoSize` or `Document` with image MIME type; max 20 MB |
| Activity text | Non-empty, max 500 characters |
| Timing label | Non-empty, max 100 characters |
| `/done` command | Session must have ≥ 1 food entry AND ≥ 1 CGM entry |
| `/trend` command | User must have ≥ 3 analysed sessions (FR-015) |

---

## Storage Paths (Constitution II)

All user-generated files MUST follow:
```
{STORAGE_ROOT}/users/{user_id}/sessions/{session_id}/
  food_{entry_id}.jpg
  cgm_{entry_id}.jpg
```

`STORAGE_ROOT` defaults to `./data` locally; set via `STORAGE_ROOT` env var for production.

---

## Data Retention

All session and analysis data retained for ≥ 90 days (SC-009, FR-014).
`expired` sessions and their entries are soft-deleted (retained in DB, file storage kept for 90 days).
