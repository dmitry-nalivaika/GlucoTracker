# Research: 004 — Bot UX: Guided Flow, Action Keyboard, Status Messages & Miro Card Enhancements

## Decision 1: Persistent Session Action Keyboard Implementation

**Decision**: Use `ReplyKeyboardMarkup` with `/done`, `/cancel`, `/status` as button
labels. These are real command strings so PTB's existing `CommandHandler` picks them up
without new text-match handlers.

**Rationale**: Command-text buttons (`/done`) are handled by existing
`CommandHandler("done", handle_done)` with zero code duplication. `ReplyKeyboardRemove`
is already called on cancel/session-end in current code. No ConversationHandler state
changes needed.

**Alternatives considered**:
- Emoji-labelled text buttons ("✅ Done") + `filters.Regex` handlers — requires adding
  3 new MessageHandlers to the SESSION_OPEN state and introduces duplication.
- InlineKeyboardMarkup — not a persistent keyboard; disappears after tap; wrong UX.

---

## Decision 2: Online Broadcast — PTB `post_init` Hook

**Decision**: Use PTB `Application.post_init` coroutine hook (supported in PTB 20+/22+).
This hook runs after the application is initialised but before polling starts, giving
access to `bot` for sending messages. The broadcast is fire-and-forget (wrapped in
`asyncio.create_task`).

**Rationale**: PTB 22.x exposes `Application.builder().post_init(cb)` where `cb` is an
async callable `(Application) -> None`. This is the idiomatic PTB hook for startup
actions. It does not block polling startup.

**Alternatives considered**:
- `JobQueue.run_once(delay=0)` — JobQueue might not be initialised at startup; timing
  is unreliable.
- Separate startup script — requires external orchestration, violates single-process design.

---

## Decision 3: `executive_summary` + `encouragement` — Prompt Extension, Not New Call

**Decision**: Add `executive_summary` (string, 2-3 sentences) and `encouragement`
(string, 1 sentence) to the existing `SESSION_ANALYSIS_SYSTEM_PROMPT`. Both fields are
parsed from `raw_response` in `miro_service.py`. No new DB columns.

**Rationale**: The existing `raw_response TEXT` column stores the full AI JSON. Adding
two fields to the prompt adds ~50 output tokens — well within the existing
`max_tokens_per_session` budget. Constitution VII allows this with no cost guard change.

**Alternatives considered**:
- New `AIAnalysis` columns (`executive_summary_text`, `encouragement_text`) — requires a
  new Alembic migration with no benefit; `raw_response` already carries all AI data.
- Separate Claude call for summary — adds cost, latency, and complexity. Rejected.

---

## Decision 4: Single-Row Photo Layout — Dynamic Frame Width

**Decision**: In `create_enhanced_session_card`, compute `images_per_row = n_images`
(all in one row). Each image uses a fixed `_IMAGE_WIDTH = 280 px` with a `_IMAGE_X_STEP = 300 px`
stride. Frame width becomes `max(1200, n_images * _IMAGE_X_STEP + 40)` — expands with
more photos.

**Rationale**: Keeping a fixed `_IMAGE_WIDTH` per image ensures readability regardless
of image count. The frame simply widens. This is the minimum change to achieve the
single-row requirement without restructuring `_upload_image`.

**Alternatives considered**:
- Shrink images proportionally to fit 1200 px — images become unreadably small for 4+
  photos.
- Two separate rows with configurable `_IMAGES_PER_ROW` — the issue explicitly requests
  a single row.

---

## Decision 5: RAG Badge — Pure Computation from `glucose_curve_json`

**Decision**: In `_build_section_text(section="glucose")`, after building the bullets,
compute the RAG badge from `in_range` values:
- Count readings where `in_range` is not null → `total_known`
- Count `in_range == True` → `in_range_count`
- Badge: 🟢 if `in_range_count / total_known >= 0.8`, 🟡 if `>= 0.5`, 🔴 if `< 0.5`,
  ⬜ if `total_known == 0`

**Rationale**: All required data is already present in `glucose_curve_json`. No new AI
call, no DB change.

**Alternatives considered**:
- Ask AI to provide a `rag_status` field — unnecessary extra prompt complexity and
  potential inconsistency vs the raw readings.

---

## Decision 6: `chat_id` Storage — Upsert-on-First-Interaction

**Decision**: Add `update_chat_id(user_id, chat_id)` to `UserRepository`. Call it from
`handle_start` (and `handle_new_session`) after ensuring the user exists. Only write if
stored `chat_id` differs from the supplied value (avoids redundant DB writes on every
message).

**Rationale**: `chat_id` only changes if a user contacts the bot from a different chat
(rare). A single conditional write is cheap.

**Alternatives considered**:
- Store in every handler — too many writes, no benefit.
- Store in middleware/hook — PTB 22 doesn't have a per-message hook without
  `Application.process_update` override; too invasive.
