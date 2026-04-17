# Contract: Telegram Bot Handlers

**Feature**: 001-telegram-mvp-session-logging | **Date**: 2026-04-17
**Library**: python-telegram-bot v22 | **Pattern**: ConversationHandler + standalone handlers

---

## Bot Commands

| Command | Description | Handler |
|---|---|---|
| `/start` | Welcome message; create user if first contact | `handle_start` |
| `/new` | Explicitly start a new session | `handle_new_session` |
| `/done` | Complete the current session and queue for analysis | `handle_done` |
| `/status` | Show current session status (entry count) | `handle_status` |
| `/trend` | Request cross-session trend analysis | `handle_trend` |
| `/help` | Display usage instructions | `handle_help` |
| `/cancel` | Discard the current open session | `handle_cancel` |

---

## Message Handlers

### Photo Message

**Trigger**: User sends a photo (Telegram `PhotoSize` message)
**Bot response flow**:
1. Identify if session is open for this user. If not, start a new session automatically.
2. Prompt user: "Is this a **food photo** or a **CGM screenshot**?"
   - Reply keyboard: `["Food photo", "CGM screenshot", "Not sure"]`
3. **If "Food photo"**: Acknowledge with "✅ Food photo saved to your session."
4. **If "CGM screenshot"**: Prompt for timing label with inline keyboard:
   - `["Before eating", "Right after eating", "1 hour after", "2 hours after", "Other"]`
   - Acknowledge with "✅ CGM screenshot ([timing]) saved to your session."
5. **If "Not sure"**: Acknowledge receipt, flag for AI clarification, ask user to describe what the image shows.
6. **On idle gap > 30 min (FR-013)**: Before accepting photo, prompt:
   - "You have an open session from [time]. Continue that session or start a new one?"
   - Reply keyboard: `["Continue session", "Start new session"]`

### Text Message

**Trigger**: User sends a text message (not a command)
**Bot response flow**:
1. If no session is open: treat as activity description and open a new session.
2. If session is open: treat as activity description. Acknowledge: "✅ Activity logged: '[text]'"
3. If in CGM timing label prompt state: treat as custom timing label.

---

## Conversation States (ConversationHandler)

```
IDLE
  → (any photo) → PHOTO_TYPE_PROMPT
  → (/new) → SESSION_OPEN
  → (/start) → IDLE

PHOTO_TYPE_PROMPT
  → ("Food photo") → SESSION_OPEN (food entry saved)
  → ("CGM screenshot") → CGM_TIMING_PROMPT
  → ("Not sure") → SESSION_OPEN (flagged entry saved)

CGM_TIMING_PROMPT
  → (timing selected) → SESSION_OPEN (cgm entry saved)
  → ("Other") → CGM_CUSTOM_TIMING (await text)

CGM_CUSTOM_TIMING
  → (text) → SESSION_OPEN (cgm entry saved with custom label)

SESSION_OPEN
  → (photo) → PHOTO_TYPE_PROMPT
  → (text) → SESSION_OPEN (activity logged)
  → (/done) → ANALYSIS_QUEUED
  → (/cancel) → IDLE
  → (/status) → SESSION_OPEN (show status)

SESSION_OPEN (idle gap detected)
  → DISAMBIGUATE_SESSION

DISAMBIGUATE_SESSION
  → ("Continue session") → SESSION_OPEN
  → ("Start new session") → SESSION_OPEN (new session)
  → (timeout 2h) → auto-close + IDLE (FR-013)

ANALYSIS_QUEUED
  → (analysis complete) → IDLE (result delivered)
```

---

## Response Timing Contract (SLOs from spec)

| Event | Target | Implementation |
|---|---|---|
| Acknowledge any input | < 2 seconds (SC-002) | Immediate handler response before any I/O |
| "Analysis in progress…" message | < 2 seconds of /done | Sent synchronously before background task |
| Analysis delivery | < 30 seconds (SC-003) | Background asyncio task |
| Miro card creation | < 5 seconds after analysis (SC-004) | Fire-and-forget after analysis delivered |

---

## Analysis Result Message Format

```
🍽️ *GlucoTrack Analysis*

*Nutrition Estimate*
Carbs: {carbs_g}g | Protein: {proteins_g}g | Fat: {fats_g}g
Glycaemic Index estimate: ~{gi_estimate}

*Glucose Curve*
{bullet list of timing_label → estimated_value_mg_dl (in/out of 70–140 mg/dL range)}

*Food–Glucose Correlation*
{correlation summary}

*Recommendations*
{numbered list of recommendations}

_{target_range_note}_
```

Telegram parse mode: `MarkdownV2`

---

## Error Messages Contract

| Error condition | User-facing message |
|---|---|
| AI analysis failure / timeout | "Sorry, analysis failed. Your session data is saved — use /done to retry." |
| CGM screenshot unreadable | "I couldn't read your CGM screenshot clearly. Please submit a clearer screenshot." |
| Miro failure (silent to user) | No user message; logged internally |
| Insufficient entries for /done | "Please add at least one food photo and one CGM screenshot before completing." |
| Insufficient sessions for /trend | "You need at least 3 analysed sessions for trend analysis. You have {n}." |
| Any unexpected error | "Something went wrong. Please try again or use /cancel to reset your session." |

**Contract rule**: Raw stack traces MUST NOT appear in any user-facing message (Constitution V).
