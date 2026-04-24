# Feature Specification: Bot UX — Guided Flow, Inline Buttons, Status Messages & Miro Card Enhancements

**Feature Branch**: `004-bot-ux-miro`
**GitHub Issue**: [#7 — feat(004): Bot UX Guided Flow, Inline Buttons, Status Messages & Miro Card Enhancements](https://github.com/dmitry-nalivaika/GlucoTracker/issues/7)
**Created**: 2026-04-24
**Status**: Draft
**Depends On**: `002-enhanced-miro-card` (must be merged first)

---

## Overview

This feature delivers two coordinated groups of improvements:

**Group A — Telegram Bot UX**: The bot interaction is redesigned to eliminate nested menus,
place all key action buttons on the first screen, guide the user step-by-step through a
logging session with conversational prompts, and communicate service availability via
online/offline status messages.

**Group B — Miro Card Enhancements**: The Miro board card layout is updated so all photos
appear in one horizontal row (food photos first, then CGM charts), the Glucose Chart
sticky note gains a RAG (Red/Amber/Green) status summary, and the Analysis sticky note
gains a top-level executive summary and a positive appreciation message.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Complete a Session Using Only First-Screen Buttons (Priority: P1)

A user opens the bot for the first time in a session and sees all the controls they need
without navigating into any sub-menu. They can start a session, add CGM screenshots with
timing labels, signal completion, and cancel — all from the initial screen. No item
requires more than one tap to reach.

**Why this priority**: The current nested CGM timing menu forces a two-tap flow that
frustrates users mid-meal. Flattening this to a single screen is the highest-impact UX
change in this feature. All other stories build on the bot being easy to use.

**Independent Test**: Can be fully tested by a new user who has never used the bot before:
open the bot, complete a session end-to-end (food photo → CGM screenshot with a timing
label → Done) using only the buttons visible on the first screen — without ever
navigating into a sub-menu.

**Acceptance Scenarios**:

1. **Given** a user opens the bot with no active session, **When** they see the initial
   screen, **Then** a **Start** button is visible and tappable without any prior navigation.
2. **Given** an active session, **When** the user wants to add a CGM screenshot, **Then**
   the CGM timing buttons (Before eating, Right after, 1 hr post, 2 hrs post) are visible
   directly on the current screen — no extra tap or sub-menu is required to reveal them.
3. **Given** an active session, **When** the user wants to finish, **Then** a **Done**
   button is visible directly on the screen without any sub-menu navigation.
4. **Given** an active session, **When** the user wants to cancel, **Then** a **Cancel**
   button is visible directly on the screen without any sub-menu navigation.
5. **Given** a user taps **Cancel** mid-session, **When** the session is cancelled,
   **Then** the bot confirms the cancellation, discards the in-progress session data, and
   returns to the initial state showing the **Start** button.
6. **Given** a user taps **Done** with no food photo yet submitted, **When** the Done
   action is evaluated, **Then** the bot rejects completion with a clear message
   explaining that at least one food photo is required before finishing.

---

### User Story 2 — Be Guided Through the Session Workflow by the Bot (Priority: P2)

When a user starts a session, the bot takes an active conversational role: it prompts
them for each type of input in sequence, confirms receipt at each step, and tells them
what to send next. The user does not need to know the expected input sequence in advance —
the bot instructs them throughout.

**Why this priority**: New and returning users currently have to remember what to send and
in what order. A guided flow eliminates this cognitive load and reduces errors (e.g.,
forgetting to send a CGM screenshot or typing the wrong thing). This is foundational for
making the product usable without a manual.

**Independent Test**: Can be tested by a user who has never seen the bot before completing
a full session solely by following the bot's prompts — without reading any documentation.
The user should be prompted for: food photo, CGM screenshot(s), activity (with skip
option), and confirmation before finishing.

**Acceptance Scenarios**:

1. **Given** a user taps **Start**, **When** the session begins, **Then** the bot sends a
   welcoming first message that explains the session objective and asks the user to send
   their first food photo.
2. **Given** the bot has prompted for a food photo and the user sends one, **When** the
   photo is received, **Then** the bot confirms receipt and prompts for a CGM screenshot,
   presenting the CGM timing buttons inline.
3. **Given** the bot has prompted for a CGM screenshot and the user selects a timing label
   and sends the screenshot, **When** the screenshot is received, **Then** the bot confirms
   receipt, records the timing, and offers: add another CGM screenshot, log activity,
   or finish the session (Done button).
4. **Given** the user is offered the activity step, **When** they tap **Skip activity**,
   **Then** the bot records no activity and presents the Done / Add more options.
5. **Given** the user taps **Done** with the minimum required inputs, **When** completion
   is triggered, **Then** the bot summarises what was collected ("1 food photo, 2 CGM
   screenshots, no activity logged") and asks the user to confirm submission.
6. **Given** the user confirms submission, **When** the session is finalised, **Then** the
   bot sends an "Analysis in progress…" message and the analysis flow begins as per
   feature 001/002.
7. **Given** the user is at any guided step, **When** they send an unexpected input type
   (e.g., a text message when a photo is expected), **Then** the bot acknowledges the
   input, explains what is expected at this step, and repeats the prompt.

---

### User Story 3 — Know Whether the Bot is Online or Offline (Priority: P3)

A user who opens the bot (or sends a message) and receives no response within a short time
is not left wondering if they did something wrong. When the bot comes online, it announces
its availability. When the bot is taken offline for maintenance, it announces that too —
so users know to try again later rather than re-sending inputs.

**Why this priority**: The user operates the bot as a one-person deployment and will
intentionally stop and start it for maintenance. Without status messages, users cannot
distinguish between "bot is processing" and "bot is down". This is placed at P3 because
it affects the meta-experience (service awareness) rather than the core logging workflow.

**Independent Test**: Can be tested by (a) starting the bot and verifying a startup
message is delivered to all known users, and (b) stopping the bot gracefully and verifying
a shutdown message was sent before the process exited.

**Acceptance Scenarios**:

1. **Given** the bot process starts, **When** it is ready to accept messages, **Then** it
   sends a status message — "✅ GlucoTrack is online and ready" (or equivalent) — to all
   users who have previously interacted with the bot.
2. **Given** the bot process is stopped gracefully (e.g., via a shutdown command or SIGTERM),
   **When** the shutdown begins, **Then** the bot sends a status message — "⏸ GlucoTrack
   is going offline for maintenance. Your data is safe." (or equivalent) — to all active
   users before exiting.
3. **Given** a user sends a message to the bot while it is offline, **When** the bot
   restarts, **Then** the startup announcement covers this — no separate "you messaged
   while I was offline" notification is required (the startup message implies it is now
   available again).
4. **Given** the bot has no known users yet (first run), **When** it starts, **Then** it
   starts silently — no broadcast attempt is made to an empty user list.

---

### User Story 4 — See a RAG Status Summary on the Glucose Chart Sticky Note (Priority: P4)

A user looking at the Miro board wants to assess a session's glucose performance at a
glance, without reading the full text. The glucose chart sticky note displays a RAG
(Red/Amber/Green) status badge and a single summary sentence that tells the user how
their glucose performed in this session relative to the 70–140 mg/dL target range.

**Why this priority**: The RAG status is a visual shortcut that makes the Miro board
scannable across many sessions. It does not change what data is stored — only how it is
displayed. It is placed at P4 because it enriches an already-working card (from feature
002) rather than unlocking new functionality.

**Independent Test**: Can be tested by generating a Miro card from a session where glucose
readings are known (all in range → Green, one slightly outside → Amber, significant
excursion → Red) and verifying the sticky note displays the correct colour and summary
sentence without requiring any other card section to be inspected.

**Acceptance Scenarios**:

1. **Given** a session where all glucose readings are within 70–140 mg/dL, **When** the
   Miro card is created, **Then** the Glucose Chart sticky note displays a **Green** status
   indicator and the summary "All readings within target range (70–140 mg/dL)."
2. **Given** a session where one or two readings are marginally outside the target range
   (140–160 mg/dL or 60–70 mg/dL), **When** the card is created, **Then** the sticky note
   displays an **Amber** status indicator and a summary noting the minor excursion (e.g.,
   "Minor excursion: 1 reading above target range").
3. **Given** a session where one or more readings are significantly outside the range
   (>160 mg/dL or <60 mg/dL), **When** the card is created, **Then** the sticky note
   displays a **Red** status indicator and a summary describing the significant deviation.
4. **Given** a session with no CGM data, **When** the card is created, **Then** the
   Glucose Chart sticky note displays a **Grey** status indicator and the message
   "No CGM data submitted for this session."
5. **Given** any RAG status is displayed, **When** a viewer reads it, **Then** the status
   label and summary are self-explanatory without requiring reference to any other section.

---

### User Story 5 — See an Executive Summary and Appreciation on the Analysis Sticky Note (Priority: P5)

A user reviewing the Miro card reads the Analysis sticky note and immediately understands
the session outcome from a 2–3 sentence executive summary at the top. Below it, a short
appreciation/encouragement message acknowledges what went well — providing positive
reinforcement alongside the detailed analysis sections from feature 002.

**Why this priority**: The executive summary and appreciation enrich the existing Analysis
sticky note (defined in feature 002) without changing its structure. They are placed last
because all five detailed analysis sub-sections from feature 002 must exist and be correct
before the summary is meaningful.

**Independent Test**: Can be tested by inspecting the Analysis sticky note of any generated
Miro card and verifying it contains: a clearly labelled "Summary" block (2–3 sentences
covering what was eaten, how glucose responded, and the key takeaway), and a clearly
labelled "Well done" / appreciation block — positioned before the five detailed sections.

**Acceptance Scenarios**:

1. **Given** a completed and analysed session, **When** the Miro card is created, **Then**
   the Analysis sticky note begins with an **Executive Summary** block containing 2–3
   sentences that cover: the meal logged, the overall glucose response, and the single
   most important takeaway or recommendation.
2. **Given** an Executive Summary block, **When** a non-technical viewer reads it,
   **Then** they can understand the key outcome of the session without reading any other
   section.
3. **Given** a session where the user's glucose stayed within the 70–140 mg/dL target
   range, **When** the card is created, **Then** the Analysis sticky note includes a
   positive **Appreciation** block that specifically acknowledges the healthy result
   (e.g., "Great job keeping your glucose in range today! 🎉").
4. **Given** a session where glucose went outside the target range, **When** the card is
   created, **Then** the Appreciation block is still present but uses encouraging framing
   (e.g., "Thanks for logging this session — every data point helps you improve!") rather
   than false praise.
5. **Given** the Executive Summary and Appreciation blocks, **When** they appear on the
   card, **Then** they are visually distinct from the five detailed analysis sub-sections
   (Food, Activity, Glucose Chart, Correlation Insight, Recommendations) and appear
   before them.

---

### User Story 6 — See All Session Photos in One Horizontal Row on the Miro Card (Priority: P6)

A user reviewing the Miro card sees all photos for the session arranged in a single
horizontal row: food photos first (in the order they were received), followed by CGM
chart screenshots. The layout makes it visually obvious which photos are food and which
are charts, and the card is easy to scan without scrolling vertically through stacked
images.

**Why this priority**: This is a layout refinement to the card introduced in feature 002.
It does not change what data is captured or analysed — only how photos are arranged. It
is placed at P6 as the lowest-priority visual polish item.

**Independent Test**: Can be tested by submitting a session with at least 2 food photos
and 1 CGM screenshot, generating the Miro card, and verifying all photos appear in one
horizontal row with food photos to the left of the CGM screenshot(s).

**Acceptance Scenarios**:

1. **Given** a session with one food photo and one CGM screenshot, **When** the Miro card
   is created, **Then** both photos appear side-by-side in a single horizontal row — food
   photo on the left, CGM screenshot on the right.
2. **Given** a session with multiple food photos, **When** the Miro card is created,
   **Then** all food photos appear in a continuous left-to-right sequence, followed
   immediately by all CGM screenshots.
3. **Given** a session with no CGM screenshots, **When** the Miro card is created,
   **Then** only food photos appear in the row — no empty placeholder slots are shown
   for absent CGM screenshots (this is specific to the photo row; the Glucose Chart
   sticky note still shows "No CGM data").
4. **Given** a session with more than 7 photos in total, **When** the card is created,
   **Then** all photos still appear in the row (wrapping to a second row only if the
   Miro card dimensions require it) — none are omitted.

---

### Edge Cases

- What happens if a user sends a food photo before tapping **Start** (i.e., without an
  active session)? The bot must prompt them to tap **Start** first and hold the photo
  in a pending state — or ask them to re-send after starting a session.
- What happens if the bot cannot reach all known users when sending the startup/shutdown
  broadcast (e.g., a user has blocked the bot)? The broadcast MUST continue to the
  remaining users; one failed delivery MUST NOT abort the broadcast.
- What happens if the guided flow is interrupted by a long silence (user goes away
  mid-session)? The existing session idle-expiry (FR-012 in feature 001) handles this —
  no new behaviour is required. The bot may optionally send a reminder after the idle
  threshold is approached.
- What happens if the AI analysis does not produce enough data to compute a RAG status?
  The sticky note falls back to a Grey "Status unavailable — analysis incomplete" indicator.
- What happens to existing Miro cards (created by features 001/002) — are they
  retroactively updated with the new photo layout and RAG status? No. Only cards created
  after this feature is deployed use the new layout.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Group A — Telegram Bot UX

- **FR-001**: The bot MUST display a **Start** button on the initial screen (no active
  session) that begins a new logging session when tapped.
- **FR-002**: The bot MUST display **Done** and **Cancel** buttons during an active session
  as persistent first-screen controls — not nested inside any sub-menu.
- **FR-003**: The CGM timing options (Before eating, Right after, 1 hr post, 2 hrs post)
  MUST be available as inline buttons on the active session screen — accessible with a
  single tap without navigating into a sub-menu.
- **FR-004**: When the bot starts, it MUST broadcast a service-online notification to all
  users who have previously interacted with the bot. A user list with zero entries MUST
  produce no broadcast attempt.
- **FR-005**: When the bot is stopped gracefully, it MUST broadcast a service-offline
  notification to all known users before the process exits. A failed delivery to one
  user MUST NOT abort the remaining broadcasts.
- **FR-006**: When a user taps **Start**, the bot MUST send a guided first message
  explaining the session goal and prompting for the first food photo.
- **FR-007**: After each input is received (food photo, CGM screenshot, activity), the bot
  MUST confirm receipt and prompt for the next expected input or offer the relevant action
  buttons for the next step.
- **FR-008**: After all inputs are collected and the user taps **Done**, the bot MUST
  present a pre-submission summary listing what was collected and ask for confirmation
  before finalising the session.
- **FR-009**: If a user sends an unexpected input type at any guided step, the bot MUST
  acknowledge the message, explain what is expected, and repeat the current step's prompt.
- **FR-010**: Tapping **Cancel** at any guided step MUST discard the in-progress session,
  confirm cancellation to the user, and return the bot to the initial Start state.
- **FR-011**: Tapping **Done** with fewer than the minimum required inputs (at least one
  food photo) MUST be rejected with a clear explanatory message; the session remains open.

#### Group B — Miro Card Enhancements

- **FR-012**: The Miro card's photo section MUST arrange all photos in a single horizontal
  row: all food photos in receipt order, followed by all CGM screenshots in receipt order.
- **FR-013**: The Glucose Chart sticky note MUST include a RAG status indicator with these
  thresholds:
  - **Green**: all glucose readings within 70–140 mg/dL
  - **Amber**: one or two readings in 140–160 mg/dL or 60–70 mg/dL (marginal excursion)
  - **Red**: one or more readings >160 mg/dL or <60 mg/dL (significant excursion)
  - **Grey**: no CGM data submitted or RAG cannot be computed from available data
- **FR-014**: The RAG status indicator on the Glucose Chart sticky note MUST be accompanied
  by a single summary sentence describing the overall glucose performance for the session.
- **FR-015**: The Analysis sticky note MUST begin with an **Executive Summary** block
  (2–3 sentences: meal overview, glucose response, key takeaway) before the five detailed
  sub-sections defined in feature 002.
- **FR-016**: The Analysis sticky note MUST include an **Appreciation** block with a
  positive, encouraging message — framed as genuine praise when glucose stayed in range,
  and as constructive encouragement when glucose went outside range.
- **FR-017**: The Executive Summary and Appreciation blocks MUST be visually distinct from
  and positioned before the five detailed analysis sub-sections (Food, Activity, Glucose
  Chart, Correlation Insight, Recommendations).
- **FR-018**: The updated photo row layout, RAG status, Executive Summary, and Appreciation
  are applied only to Miro cards created after this feature is deployed. Existing cards
  are not retroactively modified.

### Key Entities

- **BotStatus**: The operational state of the Telegram bot (online, offline). Triggers a
  broadcast notification to all known users on state transition.
- **GuidedSession**: An active logging session in which the bot is directing the user
  step-by-step. Tracks the current guided step (awaiting food photo, awaiting CGM, etc.).
  Inherits all data from the Session entity (feature 001).
- **RAGStatus**: A computed assessment of a session's glucose performance:
  Green / Amber / Red / Grey. Derived from the AIAnalysis and attached to the
  Glucose Chart sticky note on the Miro card. Belongs to one session.
- **SessionSummary**: The executive summary block displayed on the Miro Analysis sticky
  note. A 2–3 sentence distillation of the AIAnalysis. Belongs to one session.
- **SessionAppreciation**: The encouragement/appreciation block on the Miro Analysis
  sticky note. Dynamically generated based on RAGStatus and session outcome.

---

## Multi-User Isolation & Cost Compliance

**Multi-user isolation (Constitution II)**:
- The bot status broadcast reads from the full user table — the broadcast is scoped to
  users who have interacted with this bot instance (identified by Telegram user ID).
  No cross-tenant data is exposed.
- The guided session flow is per-user: each user's current guided step is stored under
  their session record. No shared guided-state structure exists.
- RAGStatus, SessionSummary, and SessionAppreciation are derived from and stored under
  the owning user's session and analysis records. They cannot be cross-referenced across users.

**Cost impact (Constitution VII)**:
- The Executive Summary and Appreciation blocks require additional AI output tokens.
  The per-session token budget MUST accommodate the extra ~100–200 tokens these fields
  are estimated to require. This MUST be validated against the $50/month cap during planning.
- The RAG status computation is rule-based (threshold comparison against existing AI
  output) and requires no additional AI call — zero additional API cost.
- The bot startup/shutdown broadcast scales linearly with the number of known users.
  At MVP scale (<50 users), the broadcast is trivially cheap. The token budget for the
  broadcast messages themselves is negligible.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can complete a full logging session (food photo → CGM
  screenshot with timing → Done → submit) using only inline buttons — without typing any
  command or navigating a sub-menu — measured by a usability walkthrough with a tester
  who has not used the bot before.
- **SC-002**: All required action buttons (Start / Done / Cancel / CGM timing options) are
  reachable with a single tap from the current screen in 100% of states tested.
- **SC-003**: The bot startup broadcast is delivered to 100% of reachable known users
  within 10 seconds of the bot process becoming ready (excluding users who have blocked
  the bot).
- **SC-004**: A Miro card generated from a session with known glucose readings displays
  the correct RAG colour (Green / Amber / Red) in 100% of test cases across all three
  threshold bands.
- **SC-005**: The Executive Summary on the Analysis sticky note is present and contains
  2–3 sentences on 100% of generated cards where an AI analysis exists.
- **SC-006**: A reviewer scanning the Miro board can identify the glucose RAG status of
  any session card within 3 seconds, without opening the full card text.
- **SC-007**: A session with 3 food photos and 2 CGM screenshots produces a Miro card
  where all 5 photos appear in a single horizontal row with food photos to the left —
  verified by visual inspection of the generated card.
- **SC-008**: The per-session AI token usage with the Executive Summary and Appreciation
  additions does not exceed the existing token budget by more than 15% — verified by
  comparing token counts before and after the prompt update.

---

## Assumptions

- The bot framework supports inline keyboard buttons with persistent visibility during
  an active session; if it does not, a command-based fallback (e.g., `/done`, `/cancel`)
  is acceptable as an alternative.
- The "known users" list for the startup/shutdown broadcast is derived from the existing
  user table (all users who have ever sent a message to the bot). No opt-in mechanism
  for broadcast notifications is in scope for this feature.
- The RAG thresholds (Green: 70–140, Amber: 60–70 or 140–160, Red: <60 or >160) are
  derived from the same 70–140 mg/dL target range used throughout the product. These
  thresholds may be revisited in a future feature if clinical guidance changes.
- The guided flow follows a linear sequence: food photo first, then CGM, then activity.
  The system still accepts inputs out of order (per feature 001 FR-004), but the bot's
  prompts follow the canonical sequence.
- The Appreciation block uses AI-generated text (as part of the same analysis call) to
  ensure it references session-specific details. It is not a fixed template string.
- The photo row layout is implemented within the constraints of the Miro API (sticky
  notes and image uploads as defined in feature 002). Wrapping beyond one row is
  acceptable when the number of photos exceeds the card's visible width.
- The Executive Summary and Appreciation blocks are generated by the AI analysis pipeline
  as additional output fields — they are not post-processed from the existing five
  sub-sections.
- The guided flow does not replace the ability to send inputs freely (a user can still
  send a photo without being explicitly prompted); the guidance is additive, not restrictive.
- Data sharing is out of scope for this feature. All session and card data defaults to
  private (Constitution II).
