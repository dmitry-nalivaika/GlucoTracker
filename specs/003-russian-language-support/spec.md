# Feature Specification: Russian Language Support — User-Selectable, All Output Layers

**Feature Branch**: `003-russian-language-support`
**GitHub Issue**: [#6 — feat(003): Russian language support — user-selectable, all output layers](https://github.com/dmitry-nalivaika/GlucoTracker/issues/6)
**Created**: 2026-04-24
**Status**: Ready for Implementation

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Switch Language Preference via Bot Command (Priority: P1)

A Russian-speaking user opens the GlucoTrack Telegram bot for the first time. All messages
arrive in English. They type `/language ru` and the bot immediately confirms that their
language has been switched to Russian. From that point forward, every message the bot sends
— prompts, confirmations, error messages — is in Russian. The preference persists across
sessions; they do not need to set it again in a future conversation.

**Why this priority**: Language preference is the prerequisite for every other story. If a
user cannot set and persist their language, none of the output-layer changes have any
effect. This must work independently of AI analysis and Miro.

**Independent Test**: Can be fully tested by a new user sending `/language ru`, verifying
the bot replies in Russian, closing the conversation, opening a new session, sending a
message, and confirming the bot still replies in Russian — without running any AI analysis
or Miro export.

**Acceptance Scenarios**:

1. **Given** a user whose preferred language is not yet set (default: English), **When**
   they send `/language ru`, **Then** the bot confirms the change in Russian and all
   subsequent bot messages to that user are in Russian.
2. **Given** a user whose language is set to Russian, **When** they send `/language en`,
   **Then** the bot confirms the change in English and all subsequent bot messages revert
   to English.
3. **Given** a user who set their language to Russian in a previous session, **When** they
   start a new Telegram session on the same account, **Then** the bot uses Russian without
   requiring them to set it again.
4. **Given** a user sends `/language xx` with an unsupported language code, **When** the
   bot processes the command, **Then** the bot replies (in the user's current language) with
   a clear error listing the supported languages and the correct command format.
5. **Given** two users — one with English preference, one with Russian — **When** they both
   interact with the bot concurrently, **Then** each receives responses exclusively in their
   own preferred language — no cross-contamination of language settings between users.

---

### User Story 2 — Receive AI Analysis in Russian (Priority: P2)

A Russian-speaking user completes a session. The AI analysis is delivered in the Telegram
bot in Russian — all five sections (food, activity, glucose chart, correlation insight,
recommendations) are written in Russian, including all numeric labels, range references,
and descriptive phrases. No English text appears in the analysis message.

**Why this priority**: The AI analysis is the primary value delivery of GlucoTrack. If it
arrives in English for a Russian-speaking user, the health insights are inaccessible. This
is the highest-value output layer after the language switch itself.

**Independent Test**: Can be tested by setting a test user's language to Russian, completing
a session, and verifying that the full analysis message contains no English text (apart from
proper nouns such as food names that have no Russian equivalent) and that all structural
labels (section headers, glucose range references) are in Russian.

**Acceptance Scenarios**:

1. **Given** a user's language is set to Russian, **When** an AI analysis is delivered,
   **Then** all section content — food breakdown, activity notes, glucose chart narrative,
   correlation insight, and recommendations — is in Russian.
2. **Given** a user's language is set to Russian, **When** the analysis references the
   70–140 mg/dL target range, **Then** the surrounding explanation text is in Russian
   (the numeric values and unit abbreviation remain as-is).
3. **Given** a user's language is set to English, **When** an AI analysis is delivered,
   **Then** the analysis is fully in English — no Russian text appears.
4. **Given** a user changes their language from Russian to English between two sessions,
   **When** the second session's analysis is delivered, **Then** it is in English, not
   Russian.

---

### User Story 3 — Miro Board Card Text in Russian (Priority: P3)

A Russian-speaking user's session is visualised on the Miro board. The card's section
labels and analysis text are in Russian. A viewer reading the card can understand the
session content without switching to another language.

**Why this priority**: The Miro card is a downstream output of the analysis. If the
analysis (P2) is in Russian, the card should match. It is P3 because it depends on the
analysis layer working first, and a Miro delivery failure is non-blocking for the user
(Telegram analysis takes priority).

**Independent Test**: Can be tested by completing a session for a Russian-language user and
verifying the resulting Miro card contains Russian text in all labelled sections, with no
English section headers.

**Acceptance Scenarios**:

1. **Given** a user's language is set to Russian, **When** the Miro card is created after
   analysis, **Then** all section labels (Food, Activity, Glucose Chart, Correlation
   Insight, Recommendations) appear in Russian.
2. **Given** a user's language is set to Russian, **When** the Miro card content is
   inspected, **Then** the analysis text within each section is in Russian, consistent with
   the Telegram analysis delivered to the same user.
3. **Given** two users — one English, one Russian — both complete sessions and their cards
   appear on the same Miro board, **When** a viewer inspects both cards, **Then** each
   card is in its respective language and there is no mixing of languages within a single
   card.

---

### User Story 4 — Trend Analysis Report in Russian (Priority: P4)

A Russian-speaking user with enough historical sessions requests a trend report via the bot.
The report is delivered entirely in Russian — session counts, pattern descriptions, range
evaluations, and recommendations are all in Russian.

**Why this priority**: Trend analysis is a downstream feature (requires multiple sessions
and depends on the analysis layer). It follows naturally from P2 and P3 but is lower
priority because trend analysis itself is deferred to a later sprint within the MVP.

**Independent Test**: Can be tested by seeding a Russian-language test user with 5+
analysed sessions and requesting a trend summary, verifying the report is in Russian with
no English text in structural elements.

**Acceptance Scenarios**:

1. **Given** a user's language is set to Russian and they have enough sessions, **When**
   they request a trend report, **Then** the full report — time period, session count,
   pattern descriptions, range evaluations, and recommendations — is in Russian.
2. **Given** a Russian-language trend report, **When** the Miro trend card is created,
   **Then** it also uses Russian text for all labels and content, consistent with the
   Telegram report.

---

### Edge Cases

- What happens when a user sends a `/language` command mid-session (while a session is
  open)? The language preference updates immediately; the current open session continues
  but any subsequent bot messages — including the analysis delivery — use the new language.
- What happens when a food item has no standard Russian name? The AI uses the transliterated
  or internationally recognised name (e.g., "бургер" for burger) rather than leaving it in
  English or producing a translation error.
- What happens if the AI is unable to generate output in Russian (e.g., returns English
  despite the language instruction)? The system delivers the output as received without
  silently corrupting or withholding it, and logs the language mismatch for operator review.
- What happens if a user's language preference record is missing (e.g., database migration
  issue)? The system defaults to English — the safe fallback — and does not fail.
- What happens when a Russian-language user sends the `/start` command for the first time?
  The onboarding message is in English by default (language not yet set). It includes a
  visible hint pointing to the `/language` command.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a bot command that allows a user to set their
  preferred output language. For this feature, the supported languages are English and
  Russian. The command MUST accept a language code and confirm the change to the user.
- **FR-002**: The system MUST store each user's language preference persistently and
  associate it with their user identity. The preference MUST survive across bot sessions,
  app restarts, and deployments.
- **FR-003**: All Telegram bot messages sent to a user MUST be delivered in that user's
  stored language preference, including: session prompts, input acknowledgements,
  disambiguation questions, error messages, "analysis in progress" messages, analysis
  delivery, and trend reports.
- **FR-004**: The AI analysis pipeline MUST be instructed to produce its output in the
  requesting user's preferred language. The instruction MUST apply to all five analysis
  sections: food breakdown, activity explanation, glucose chart narrative, correlation
  insight, and recommendations.
- **FR-005**: The Miro board card MUST use the session owner's language preference for all
  section labels and analysis text. A card created for a Russian-preference user MUST
  contain Russian text; a card for an English-preference user MUST contain English text.
- **FR-006**: Trend analysis reports MUST be delivered in the requesting user's preferred
  language, including the Miro trend card generated after the report.
- **FR-007**: If a user sends an unsupported language code, the system MUST respond in
  the user's current language (before the attempted change) with a message listing the
  supported languages and the correct command syntax.
- **FR-008**: When no language preference has been set for a user, the system MUST default
  to English for all output.
- **FR-009**: The language preference system MUST be designed so that additional languages
  can be added in future without structural changes — only new translation content and an
  extension of the supported-language list should be required.
- **FR-010**: Language preference MUST be scoped per user. Changing one user's language
  MUST NOT affect any other user's language setting or output.

### Key Entities

- **UserLanguagePreference**: A persisted record associating a user with their chosen
  output language. Has one entry per user. Defaults to English if absent. Updated by the
  language command.
- **SupportedLanguage**: An enumerated set of languages the system can produce output in.
  Initial set: English (`en`), Russian (`ru`). Extensible for future languages.

---

## Multi-User Isolation Compliance

*Required for features that touch user data (Constitution II).*

- Language preference is stored as a per-user attribute, always scoped by `user_id`.
- No user's language preference is readable or writable by another user.
- The AI analysis language instruction is derived from the session owner's preference at
  the time of analysis — not from any shared or global setting.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who sets their language to Russian receives 100% of subsequent bot
  messages in Russian — verified across all message types (prompt, acknowledgement, error,
  analysis, trend report) in a test run of 10 complete sessions.
- **SC-002**: Language preference persists across sessions — verified by setting Russian
  preference, closing the bot, re-opening, and confirming the first bot response is in
  Russian without re-issuing the `/language` command.
- **SC-003**: The AI analysis for a Russian-preference user contains no English structural
  labels or section headers — verified by automated text inspection on 10 test analyses.
- **SC-004**: A Miro card created for a Russian-preference user has all section labels and
  analysis text in Russian — verified by card content inspection on 5 test sessions.
- **SC-005**: Two concurrent users (one English, one Russian) receive analysis in their
  respective languages with zero cross-contamination — verified by running parallel test
  sessions.
- **SC-006**: Switching language mid-use (from English to Russian or vice versa) takes
  effect on the next bot message — verified by measuring the message immediately after the
  `/language` command response.
- **SC-007**: An unsupported language code returns a graceful, human-readable error message
  in the user's current language within 2 seconds — verified by sending `/language xx`
  with 3 different invalid codes.
- **SC-008**: The language preference system introduces no measurable latency increase to
  the bot acknowledgement SLO (< 2 seconds) — verified by timing 50 bot interactions with
  and without language lookup.

---

## Assumptions

- The initial supported languages in this feature are English (`en`) and Russian (`ru`)
  only. Additional languages (e.g., German, Spanish) are explicitly out of scope and
  addressed in a future feature.
- The bot command for setting language is `/language <code>` (e.g., `/language ru`,
  `/language en`). Variant forms such as `/lang` are not required in this feature.
- Food item names that have no established Russian equivalent are represented using
  transliteration or internationally recognised borrowed terms — the AI is trusted to
  handle this naturally without a separate translation dictionary.
- The 70–140 mg/dL numeric range and the unit abbreviation "mg/dL" are not translated —
  they are universally recognised medical notation. All surrounding text is translated.
- The onboarding message (`/start` response) for a first-time user defaults to English and
  includes a visible hint about the `/language` command. A fully localised onboarding
  experience is out of scope for this feature.
- Language preference is stored at the user level, not the session level — every session
  for a given user uses the same language. Per-session language override is out of scope.
- If a user changes language while an analysis is already running, the in-flight analysis
  completes in the language that was set when the analysis started. The new preference
  takes effect for the next session.
- Data sharing is out of scope for this feature. All language preferences default to
  private (accessible only by the owning user's requests).
