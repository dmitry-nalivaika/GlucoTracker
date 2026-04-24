# Feature Specification: 004 — Bot UX: Guided Flow, Action Keyboard, Status Messages & Miro Card Enhancements

**GitHub Issue**: #7
**Branch**: `004-bot-ux-guided-flow-miro-enhancements`
**Depends on**: `002-enhanced-miro-card` (merged), `003-russian-language-support` (merged)

---

## Overview

A coordinated set of UX improvements across the Telegram bot and the Miro board
visualisation layer. The goals are:

1. Guide users step-by-step through the logging workflow with clear next-action prompts.
2. Keep Done/Cancel/Status always accessible via a persistent reply keyboard.
3. Broadcast bot online/offline messages so users know service availability.
4. Enrich Miro cards with a RAG status badge, executive summary, and a cleaner photo row.

---

## User Stories

### US1 — Guided Conversational Flow + Session Action Keyboard (P1)

**As a user** I want the bot to tell me exactly what to do next at every step, and
I want Done/Cancel/Status always one tap away, so I can complete a session confidently
without memorising commands.

**Acceptance Criteria**:

- AC1.1: After `/new` (or `/start` with no open session), the bot sends a guided
  next-step prompt telling the user to send a food photo, AND shows a
  `ReplyKeyboardMarkup` with buttons `/done`, `/cancel`, `/status`.
- AC1.2: After a **food photo** is saved, the ack message includes a next-step hint:
  "Send another food photo, or send your CGM screenshot, or tap /done when ready."
- AC1.3: After a **CGM screenshot** is saved, the ack message includes a next-step hint:
  "Send another CGM screenshot, describe your activity, or tap /done."
- AC1.4: After **activity text** is saved, the ack includes a next-step hint:
  "Add more photos if needed, or tap /done for your analysis."
- AC1.5: All guided prompt strings are bilingual (en/ru) via i18n catalogue.
- AC1.6: The session action keyboard is shown with `/done`, `/cancel`, `/status`
  buttons whenever `new_session_started` is acked.
- AC1.7: The session action keyboard is dismissed (`ReplyKeyboardRemove`) when a
  session ends (via /cancel or after analysis is queued).

---

### US2 — Bot Online/Offline Status Messages (P2)

**As a user** I want to receive a message when the bot comes online (or goes offline)
so I know whether the service is available.

**Acceptance Criteria**:

- AC2.1: When the bot application starts, it broadcasts a "🟢 GlucoTrack is online!"
  message to all users who have a stored `chat_id`.
- AC2.2: The broadcast is fire-and-forget; it MUST NOT block bot startup.
- AC2.3: The `users` table gains a `chat_id BIGINT NULL` column (migration 004).
- AC2.4: Every handler that has `update.effective_chat` stores `chat_id` for the user
  on first interaction (upsert, no duplicate writes on each message).
- AC2.5: The online message is bilingual (uses the stored `language_code`).
- AC2.6: Offline broadcast is optional — only if the PTB Application supports a clean
  post-stop hook; otherwise it is a no-op (graceful degradation).

---

### US3 — Miro Card Enhancements (P3)

**As an analyst** I want the Miro card to show a RAG glucose status, an executive
summary, and photos in a clean single row so I can evaluate a session at a glance.

**Acceptance Criteria**:

- AC3.1 (Single-row photos): All session photos (food first, CGM second) are rendered
  in **one horizontal row** inside the frame.  The frame width scales to accommodate
  all images at a fixed per-image width of 300 px with 20 px gaps; existing
  `_IMAGE_HEIGHT` constraint is kept.
- AC3.2 (RAG badge): The glucose sticky note header includes a RAG badge:
  - 🟢 Green: ≥ 80 % of readings `in_range = True`
  - 🟡 Amber: 50–79 % of readings in range
  - 🔴 Red: < 50 % of readings in range
  - ⬜ Unknown: no readings with known `in_range` value
- AC3.3 (Executive summary sticky note): A new grey sticky note (position: row 3,
  spanning both columns — i.e. placed at column-centre of the full frame) contains:
  - `executive_summary`: 2–3 sentence top-level session summary from the AI response
  - `encouragement`: one sentence of positive appreciation from the AI response
- AC3.4: `executive_summary` and `encouragement` are added to
  `SESSION_ANALYSIS_SYSTEM_PROMPT`; they are stored in `raw_response` (no new DB
  columns).
- AC3.5: All new Miro strings are bilingual via i18n (`miro_executive_summary_header`,
  `miro_encouragement_header`).
- AC3.6: If `executive_summary` / `encouragement` are absent from the AI response
  (legacy sessions), the summary sticky note shows a graceful fallback.

---

## Non-Functional Requirements

- NFR-1: Bot startup broadcast MUST NOT increase startup latency perceptibly (fire-and-forget).
- NFR-2: All new strings follow the existing MarkdownV2 escaping convention in i18n.py.
- NFR-3: Miro frame height and section offsets must update correctly when photo count changes.
- NFR-4: All new DB queries include `user_id` scope (Constitution II).
- NFR-5: No new Claude API calls are introduced for RAG status or executive summary beyond
  the existing single `analyse_session` call per session.

---

## Out of Scope

- Restructuring the 3-step photo → classify → timing conversation flow (deferred).
- Offline broadcast (AC2.6): graceful no-op if PTB does not provide a clean hook.
- Trend analysis improvements (separate feature).

---

## Constitution Compliance

### Principle II (Multi-User Isolation)
- `chat_id` stored per user, scoped by `user_id`.
- Online broadcast iterates only users with `chat_id IS NOT NULL`.
- All repository queries include `user_id` predicate.

### Principle VII (Cost Management)
- No additional Claude API calls — `executive_summary` and `encouragement` are added to
  the **existing** single prompt call. Token overhead is minor (~50 tokens per response).
- No new Azure services.
