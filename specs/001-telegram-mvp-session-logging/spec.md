# Feature Specification: GlucoTrack Telegram MVP — Session Logging & AI Analysis

**Feature Branch**: `001-telegram-mvp-session-logging`
**GitHub Issue**: [#1 — feat(001): Telegram MVP — Session Logging & AI Analysis](https://github.com/dmitry-nalivaika/GlucoTracker/issues/1)
**Created**: 2026-04-17
**Status**: Ready for Implementation
**Input**: User description: GlucoTrack MVP — Telegram bot input, AI session analysis, Miro board output

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Log a Meal Session via Telegram (Priority: P1)

A user wearing a CGM eats a meal and wants to record it for glucose analysis. They open
the GlucoTrack Telegram bot and send a food photo, one or more CGM screenshots taken at
key moments around the meal (before eating, right after, 1 hour post, 2 hours post), and
an optional short text describing any physical activity. Once they finish sending inputs,
they signal the end of the session. The system acknowledges the session is complete and
queued for analysis.

**Why this priority**: This is the foundational user interaction. Without the ability to
submit a session, all other functionality is unreachable. It must work reliably before AI
analysis or visualisation are added.

**Independent Test**: Can be fully tested by sending a food photo + one CGM screenshot
to the bot, completing the session, and verifying the bot confirms receipt of a complete,
persisted session tagged to the user's identity — without any AI analysis running.

**Acceptance Scenarios**:

1. **Given** a registered user opens the Telegram bot, **When** they send a food photo,
   **Then** the bot acknowledges receipt and confirms it is waiting for more inputs for
   the current session.
2. **Given** an open session, **When** the user sends a CGM screenshot with a timing
   label (e.g. "before eating", "1 hour after"), **Then** the bot confirms the screenshot
   is added to the session.
3. **Given** an open session, **When** the user sends a text activity log (e.g. "ran
   1 km"), **Then** the bot confirms the activity is recorded in the session.
4. **Given** an open session with at least one food photo and one CGM screenshot,
   **When** the user signals session completion, **Then** the bot confirms the session is
   saved and queued for AI analysis.
5. **Given** a completed session, **When** another user sends inputs to the bot,
   **Then** the second user's session is fully isolated from the first user's data.
6. **Given** a user sends inputs out of expected order (e.g. activity before food photo),
   **Then** the system accepts all inputs regardless of order without data loss.

---

### User Story 2 — Receive AI Analysis of a Session (Priority: P2)

After a session is complete, the user receives a structured AI-generated analysis within
the Telegram bot. The analysis covers: estimated nutritional content of the meal
(carbohydrates, proteins, fats, glycaemic index estimate), the glucose curve extracted
from the CGM screenshots, a correlation between food/activity and the glucose response
(spikes, dips, stable zones), and personalised recommendations for improving glucose
stability.

**Why this priority**: This is the core value proposition of GlucoTrack. Users log data
specifically to receive actionable insights. Without analysis, the app is a data logger
with no return value.

**Independent Test**: Can be tested by submitting a test session with known food and CGM
data, triggering analysis, and verifying the response contains all four sections (nutrition
estimate, glucose curve, correlation, recommendations) with plausible content.

**Acceptance Scenarios**:

1. **Given** a completed session queued for analysis, **When** the AI analysis finishes,
   **Then** the user receives a message in Telegram containing: nutritional summary,
   glucose curve summary, food-glucose correlation insight, and at least one recommendation.
2. **Given** an analysis result, **When** the user reviews it, **Then** all four sections
   are clearly separated and labelled so the user can read them independently.
3. **Given** a session with no physical activity logged, **When** analysis runs,
   **Then** the activity section is omitted or marked "no activity logged" — the analysis
   does not error or produce placeholder content.
4. **Given** a session where the CGM screenshot cannot be parsed (e.g. blurry, cropped),
   **When** analysis runs, **Then** the user receives an informative message explaining
   the issue and asking them to re-submit a clearer screenshot rather than silently
   failing or producing a misleading result.
5. **Given** an analysis is delivered, **When** the user is the only person who submitted
   this session, **Then** the analysis content is visible only to that user — no other
   user receives it or can access it.

---

### User Story 3 — Visualise Session on Miro Board (Priority: P3)

After AI analysis completes, a structured card representing the session and its analysis
is automatically posted to a pre-configured Miro board. The card includes the session
timestamp, a summary of the food logged, the glucose response summary, and the key
recommendation(s). The Miro board accumulates cards over time, forming a visual history
of the user's sessions.

**Why this priority**: Miro is the MVP visualisation layer — a temporary replacement for
a dedicated dashboard. It must exist for the MVP to deliver a complete user journey, but
it can be the last piece because the core value (analysis in Telegram) works without it.

**Independent Test**: Can be tested by completing a session + analysis and verifying a
new Miro card appears on the designated board with correct content matching the analysis
output delivered in Telegram.

**Acceptance Scenarios**:

1. **Given** an AI analysis has been delivered to the user, **When** the Miro export
   runs, **Then** a new card appears on the configured Miro board within 5 seconds of
   analysis completion.
2. **Given** a Miro card is created, **When** a reviewer inspects it, **Then** it
   contains: session date/time, food summary, glucose response summary, and primary
   recommendation — all matching the Telegram analysis message.
3. **Given** the Miro API is unavailable, **When** the export is attempted, **Then**
   the user is still notified of their analysis in Telegram (Miro failure MUST NOT block
   the primary analysis delivery), and the system retries the Miro export automatically.
4. **Given** multiple users have logged sessions, **When** the Miro board is viewed,
   **Then** each user's cards are visually distinct and labelled with an anonymised
   user identifier (not their Telegram username or personal data).

---

### User Story 4 — Cross-Session Trend Analysis (Priority: P4 — MVP, deferred sprint)

After a user has logged several sessions over multiple days, they can request a trend
summary from the Telegram bot. The system analyses their accumulated session history and
delivers a personalised report highlighting what is improving, what is worsening, and
what consistent patterns exist in their glucose response to food and activity choices.

**Why this priority**: Trend analysis is explicitly part of the product vision and
transforms GlucoTrack from a session logger into a long-term health companion. It is
deferred within the MVP (requires accumulated data) but must be designed for from the
start — the data model and storage must support it.

**Independent Test**: Can be tested by seeding a test user with 5+ historical sessions
and verifying the trend report references data across multiple sessions, identifies at
least one positive and one negative pattern, and relates them to the 70–140 mg/dL
target range.

**Acceptance Scenarios**:

1. **Given** a user has at least 3 completed and analysed sessions, **When** they request
   a trend summary, **Then** the bot delivers a report covering: overall glucose stability
   trend, foods/activities correlated with staying within the 70–140 mg/dL target range,
   and foods/activities correlated with spikes or dips outside the target range.
2. **Given** a trend report is delivered, **When** the user reviews it, **Then** the
   report references the historical time period it covers (e.g. "based on your last 7
   days") and the number of sessions analysed.
3. **Given** a user has fewer than 3 analysed sessions, **When** they request a trend
   summary, **Then** the bot informs them how many more sessions are needed before trends
   can be meaningfully identified — it does not generate a report from insufficient data.
4. **Given** a trend report is generated, **When** it is delivered, **Then** it includes
   at least one specific, actionable recommendation (e.g. "your glucose stays most stable
   after meals with X — consider prioritising those").
5. **Given** a trend report is generated, **When** the Miro board is updated, **Then** a
   dedicated trend card is posted alongside the session cards, visually distinct and
   dated.

---

### Edge Cases

- What happens when a user sends a photo that is not a food photo or a CGM screenshot
  (e.g. a random image)? The system should acknowledge receipt but flag ambiguity and
  ask the user to clarify what the image represents.
- What happens when the AI analysis call fails or times out? The user must receive an
  error message with guidance to retry; the session data must be preserved for re-analysis.
- What happens when a user abandons a session without completing it? The session should
  be discarded or auto-expired after a defined idle period to avoid orphaned data.
- What happens when a user sends more than one food photo in a single session? All
  photos should be included in the session and the AI should analyse them collectively.
- What happens when the Telegram bot receives a message from an unknown/unregistered
  user? The bot must create a new user identity (Telegram user ID as the identifier)
  transparently, without requiring any sign-up flow for the MVP.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST operate as a Telegram bot that receives messages from users
  (photos, screenshots, text) as the primary input channel for the MVP.
- **FR-002**: The system MUST identify each user uniquely by their Telegram user ID and
  associate all submitted data with that identity at write time.
- **FR-003**: The system MUST group messages from a single user into a named "session"
  representing one meal/activity event.
- **FR-004**: The system MUST support the following input types within a session:
  (a) food photographs, (b) CGM app screenshots, (c) free-text activity descriptions.
- **FR-005**: The system MUST allow users to label CGM screenshots with a timing context
  (before eating, right after, 1 hour post-meal, 2 hours post-meal).
- **FR-006**: The system MUST store all session inputs (photos, screenshots, text) in
  user-namespaced storage paths following the pattern `/users/{user_id}/sessions/{session_id}/`.
- **FR-007**: The system MUST send the completed session to an AI analysis pipeline that
  produces: nutritional estimation (carbohydrates, proteins, fats, glycaemic index),
  glucose curve summary (values and timing extracted from CGM screenshots), food-glucose
  correlation (spikes, dips, stable zones), and personalised recommendations. All analysis
  MUST evaluate glucose values against the healthy target range of **70–140 mg/dL** and
  explicitly note when the user's readings exceeded or fell below that range.
- **FR-008**: The system MUST deliver the AI analysis result to the user as a structured
  Telegram message with clearly separated sections.
- **FR-009**: The system MUST post a summary card to a pre-configured Miro board after
  analysis completes; Miro failure MUST NOT prevent Telegram delivery.
- **FR-010**: The system MUST enforce data isolation — no user's session data, analysis,
  or stored files may be accessible by any other user.
- **FR-011**: The system MUST handle unparseable CGM screenshots gracefully by notifying
  the user and preserving session data for re-submission.
- **FR-012**: The system MUST auto-expire incomplete (abandoned) sessions after an idle
  period to prevent orphaned data accumulation.
- **FR-014**: The system MUST persist all session and analysis data in a queryable form
  so that cross-session trend analysis can be performed. Data retention MUST cover at
  minimum the last 90 days of a user's sessions.
- **FR-015**: When a user requests a trend summary (via a bot command), the system MUST
  retrieve that user's historical analysed sessions, run a trend analysis, and deliver a
  structured report as defined in User Story 4. A minimum of 3 analysed sessions is
  required; the system MUST NOT generate a trend report with fewer.
- **FR-016**: The trend analysis MUST reference the 70–140 mg/dL target range explicitly
  in identifying patterns of stability, spikes, and dips across sessions.
- **FR-013**: When a user sends a message after a gap of more than a configurable idle
  threshold (default: 30 minutes) since their last input, the bot MUST ask the user
  whether they want to continue the existing open session or start a new one. The user's
  explicit choice determines whether the new input is appended to the existing session or
  opens a fresh session. If the user does not respond to the disambiguation prompt within
  2 hours, the existing session MUST be automatically closed and queued for analysis, and
  the new message begins a fresh session.

### Key Entities

- **User**: Identified by Telegram user ID. Owns all sessions and their associated data.
- **Session**: A time-bounded collection of inputs (food photos, CGM screenshots, activity
  notes) representing one meal/activity event. Has a status: open, completed, analysed, expired.
- **FoodEntry**: One food photograph within a session, plus optional free-text description.
- **CGMEntry**: One CGM screenshot within a session, labelled with a timing context.
- **ActivityEntry**: A free-text description of physical activity within a session.
- **AIAnalysis**: The structured result of analysing a session. Contains: nutrition estimate,
  glucose curve data, correlation insights, recommendations. Belongs to exactly one session.
- **MiroCard**: A read-only visualisation artefact created from an AIAnalysis or a
  TrendAnalysis. References the source but is not the source of truth.
- **TrendAnalysis**: A cross-session analysis result covering a user's historical
  sessions. Contains: time period covered, session count, patterns within/outside the
  70–140 mg/dL range, and actionable recommendations. Belongs to one user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can complete the full flow — open a session, submit food photo +
  CGM screenshot + activity note, receive AI analysis — in under 5 minutes of elapsed
  clock time.
- **SC-002**: The bot acknowledges each submitted input within 2 seconds of receipt.
- **SC-003**: AI analysis is delivered to the user within 30 seconds of session completion
  under normal operating conditions.
- **SC-004**: A Miro card appears on the board within 5 seconds of analysis completion.
- **SC-005**: 100% of stored session artefacts (photos, screenshots, analysis) are tagged
  with the owning user's identifier — verifiable by inspecting stored data paths and records.
- **SC-006**: A test user cannot retrieve, view, or reference any data belonging to a
  different test user under any scenario — verified by cross-user access attempts returning
  empty or permission-denied results.
- **SC-007**: The system remains within the $50/month cost cap at a usage volume of up to
  50 session analyses per day.
- **SC-008**: A user with 5 or more analysed sessions can receive a trend report that
  references the 70–140 mg/dL target range and names at least one food or activity
  pattern correlated with staying within or outside that range.
- **SC-009**: All session and analysis data is retained and queryable for at least 90 days,
  enabling retrospective trend analysis without data loss.

## Assumptions

- For the MVP, a user's Telegram user ID is their complete identity — no separate account
  creation, email, or password is required. The system creates a user record automatically
  on first contact.
- CGM screenshot timing labels (before eating, right after, etc.) are provided by the user
  as free text or selected from a short menu presented by the bot; the system does not
  attempt to infer timing from image metadata.
- The Miro board is pre-configured by the operator (board ID stored in system config);
  users do not select or manage their own Miro board in the MVP.
- Each user posts to the same shared Miro board, with user-scoped card labelling for
  visual separation (no per-user board provisioning in MVP).
- A session may contain multiple food photos (e.g. start and end of a meal); all are
  passed to the AI for collective analysis.
- The AI analysis pipeline may take up to 30 seconds; the bot sends an intermediate
  "Analysis in progress…" message to prevent the user from assuming the system has failed.
- Sessions involving only activity entries (no food photo) are out of scope for MVP —
  at least one food photo is required for a valid, analysable session.
- Physical activity is optional within a session; its absence does not prevent analysis.
- **Data sharing is out of scope for this feature.** The architecture supports it
  (ACL-based sharing model per the constitution) but no sharing UI, sharing commands, or
  access control UI will be built in this feature. A separate feature will implement
  sharing with nutritionists, family members, and groups. All data defaults to private.
- Trend analysis (User Story 4 / FR-014–016) is included in this spec but deferred to a
  later sprint within the MVP. The data model and storage MUST be designed to support it
  from the start; the trend analysis command need not be functional in the first release.

