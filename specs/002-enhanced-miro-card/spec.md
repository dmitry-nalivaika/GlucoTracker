# Feature Specification: Enhanced Miro Board Card with Embedded Photos and Rich AI Analysis

**Feature Branch**: `002-enhanced-miro-card`
**GitHub Issue**: [#3 — feat(002): Enhanced Miro Board Card with Embedded Photos and Rich AI Analysis](https://github.com/dmitry-nalivaika/GlucoTracker/issues/3)
**Created**: 2026-04-23
**Status**: Ready for Implementation
**Depends On**: `001-telegram-mvp-session-logging` (must be merged first)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — View Full Session as a Visual Miro Card (Priority: P1)

A user who has completed a session via the Telegram bot later opens the Miro board to
review what they logged. Instead of a plain text summary, they see a rich, structured card
that shows exactly what they submitted — the food photo(s) and CGM screenshots displayed
as embedded images — alongside a comprehensive AI analysis broken into clearly labelled
sections. The user can understand their entire meal event at a glance without returning to
Telegram.

**Why this priority**: This is the core value of the feature. If the card does not display
the input photos and the full analysis, the feature has not delivered on its promise. All
other stories depend on this foundation working correctly.

**Independent Test**: Can be fully tested by completing a session with one food photo and
one CGM screenshot, triggering analysis, and verifying the resulting Miro card contains
both images embedded inline and all five analysis sections with substantive content —
without any changes to the Telegram delivery flow.

**Acceptance Scenarios**:

1. **Given** a session has been analysed, **When** the Miro card is created, **Then** the
   card contains a clearly labelled input data section that shows all food photos submitted
   in the session embedded as visible images within the card frame.
2. **Given** a session has been analysed, **When** the Miro card is created, **Then** all
   CGM screenshots submitted in the session are also embedded as visible images within the
   card frame, alongside the food photos.
3. **Given** a session with multiple food photos and multiple CGM screenshots, **When** the
   Miro card is created, **Then** every photo and every screenshot appears on the card —
   none are omitted.
4. **Given** a Miro card has been created, **When** a viewer inspects it, **Then** they can
   identify the input section (top of card) and the analysis section (below) without any
   supplementary instructions.
5. **Given** a session with no physical activity logged, **When** the Miro card is created,
   **Then** the activity section is marked "No activity logged" rather than omitted, so the
   card layout remains consistent.

---

### User Story 2 — Understand Food Impact from the Miro Card (Priority: P2)

A user reviews their Miro card and wants to understand what they ate and how those specific
foods were expected to affect their blood glucose. The card's Food section explains the
estimated nutritional composition of the meal and provides a narrative of the expected
glycaemic effect, referenced against the 70–140 mg/dL target range.

**Why this priority**: The food explanation is the most frequently reviewed section because
every session includes food. It directly supports the product's core purpose — helping users
understand what to eat to maintain healthy glucose levels.

**Independent Test**: Can be tested by submitting a session with a recognisable food photo,
and verifying the Miro card's Food section contains an estimated nutritional breakdown
(carbohydrates, proteins, fats, glycaemic index category) and at least one sentence
describing expected glucose impact — without requiring the CGM or activity sections to be
populated.

**Acceptance Scenarios**:

1. **Given** a completed session, **When** the Miro card is generated, **Then** the Food
   section contains an estimated nutritional breakdown covering: carbohydrates (g),
   proteins (g), fats (g), and a glycaemic index category (low/medium/high).
2. **Given** a Food section has been generated, **When** a viewer reads it, **Then** it
   includes a narrative explaining how this meal's composition is expected to influence
   blood glucose — referencing the 70–140 mg/dL target range explicitly.
3. **Given** a session with multiple food photos, **When** the Food section is generated,
   **Then** it analyses the collective meal across all submitted photos, not each photo in
   isolation.

---

### User Story 3 — Understand Glucose Response from the Miro Card (Priority: P3)

A user reviews the Miro card's Glucose Chart section and reads a narrative of their glucose
curve. The section tells them the values recorded at each CGM timing point, whether those
values were within the healthy 70–140 mg/dL target range, and describes the shape of the
curve (e.g., spike and recovery, stable plateau, gradual rise).

**Why this priority**: The glucose chart narrative is the diagnostic output — it tells the
user what actually happened, not just what was expected. It is the bridge between the food
they logged and the AI correlation insight.

**Independent Test**: Can be tested by submitting a session with one or more CGM
screenshots labelled with timing contexts, and verifying the Miro card's Glucose Chart
section contains: at least one numeric glucose value, a statement about whether readings
were within or outside the 70–140 mg/dL range, and a descriptive phrase characterising
the curve shape.

**Acceptance Scenarios**:

1. **Given** a session with CGM screenshots at multiple timing points, **When** the Glucose
   Chart section is generated, **Then** it lists a glucose reading or range for each timing
   point provided (before eating, right after, 1 hour post, 2 hours post as applicable).
2. **Given** any glucose reading in the session, **When** the Glucose Chart section is
   generated, **Then** each value is explicitly evaluated against the 70–140 mg/dL target
   range with a clear statement: within range, above range, or below range.
3. **Given** a Glucose Chart section, **When** a viewer reads it, **Then** it includes a
   descriptive label for the curve shape (e.g., "sharp spike with recovery", "stable within
   range", "gradual rise without return to baseline") so the viewer can characterise the
   session without interpreting raw numbers.
4. **Given** a CGM screenshot that cannot be parsed (too blurry or cropped), **When** the
   Glucose Chart section is generated, **Then** that timing point is marked "unreadable"
   with an advisory to re-submit — the section is not omitted entirely.

---

### User Story 4 — Understand Cause-and-Effect via Correlation Insight (Priority: P4)

A user reads the Correlation Insight section on the Miro card and gains an explicit
understanding of how their food choices and physical activity together produced the observed
glucose curve. The section provides cause-and-effect reasoning — not just summaries —
explaining which aspects of the meal or activity are likely responsible for specific
features of the curve (spikes, dips, stable zones).

**Why this priority**: This is the insight that differentiates GlucoTrack from a simple
logger. Without causal reasoning, users cannot make informed changes to their diet or
activity. It is placed at P4 because it builds on the Food (P2) and Glucose (P3) sections
being correct first.

**Independent Test**: Can be tested by verifying the Correlation Insight section contains
at least two causal statements of the form "because of X, the glucose response showed Y",
referencing specific foods, activities, or combinations from the same session.

**Acceptance Scenarios**:

1. **Given** a session with both food and activity data, **When** the Correlation Insight
   section is generated, **Then** it explicitly links named foods or food components to
   specific observed glucose behaviours (e.g., "the high-carbohydrate portion likely caused
   the spike at the 1-hour mark").
2. **Given** a session where activity was logged, **When** the Correlation Insight section
   is generated, **Then** it explains how the activity modulated the glucose response —
   either by dampening a spike, accelerating recovery, or having minimal observable effect.
3. **Given** a session with no activity logged, **When** the Correlation Insight section is
   generated, **Then** it focuses exclusively on the food-glucose link and does not
   fabricate activity effects.
4. **Given** the Correlation Insight section, **When** a non-technical user reads it,
   **Then** the explanation uses plain language without medical jargon — all terms are
   self-explanatory within the card context.

---

### User Story 5 — Receive Actionable Recommendations on the Miro Card (Priority: P5)

The Miro card's Recommendations section contains specific, actionable suggestions tailored
to the exact meal type and activity combination in the session. The suggestions help the
user understand what they could do differently — or should keep doing — to maintain glucose
levels within the 70–140 mg/dL range.

**Why this priority**: Recommendations are the call-to-action that converts insights into
behaviour change. They are placed last because they require all preceding sections (food,
glucose, correlation) to be correct before the recommendations are meaningful.

**Independent Test**: Can be tested by verifying the Recommendations section contains at
least one suggestion that references something specific from the session (a named food, the
activity type, or a timing pattern) rather than generic advice, and that the suggestion
explicitly relates to maintaining or returning to the 70–140 mg/dL range.

**Acceptance Scenarios**:

1. **Given** a session where glucose exceeded 140 mg/dL, **When** Recommendations are
   generated, **Then** at least one recommendation addresses how to reduce the post-meal
   spike for this meal type specifically.
2. **Given** a session where glucose stayed within 70–140 mg/dL throughout, **When**
   Recommendations are generated, **Then** at least one recommendation reinforces the
   positive behaviour and explains why it worked.
3. **Given** any session, **When** Recommendations are generated, **Then** each
   recommendation is phrased as a concrete action (e.g., "add a 15-minute walk after this
   type of meal") not a general principle (e.g., "exercise more").
4. **Given** a completed Miro card, **When** the Miro export is compared to the Telegram
   analysis message, **Then** the Recommendations on the card are consistent with those
   delivered in Telegram — they are not contradictory or divergent.

---

### Edge Cases

- What happens if the Miro API rejects an image upload (file size too large, unsupported
  format)? The card must still be created with the analysis text; the failed image slot is
  replaced with a placeholder noting "image unavailable".
- What happens if the AI analysis produces an empty or malformed analysis section? Each
  section must have a fallback message ("Analysis unavailable for this section — please
  re-submit your session") rather than leaving a blank section on the card.
- What happens if the session has no CGM screenshots? The Glucose Chart section displays
  "No CGM data submitted for this session" — no fabricated glucose values appear.
- What happens if the Miro card creation exceeds the 5-second SLO? The failure is logged,
  the user receives their Telegram analysis unaffected, and the system retries the Miro
  card creation automatically (per the existing FR-009 retry behaviour).
- What happens when a viewer opens the Miro board and sees cards from multiple users?
  Each card is labelled with an anonymised identifier — no personal data (name, Telegram
  username, phone number) appears on or in the card.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST upload all food photos and CGM screenshots from a session
  directly to the Miro card frame as embedded images visible without clicking or expanding
  any element.
- **FR-002**: Embedded images MUST be arranged with all food photos followed by all CGM
  screenshots, in the order they were received. If there are multiple photos, they MUST all
  appear — none omitted.
- **FR-003**: The Miro card MUST be structured into two top-level sections: (a) Input Data
  (images) at the top, and (b) Analysis (text) below. The visual separation between these
  sections MUST be clear.
- **FR-004**: The Analysis section of the card MUST contain five labelled sub-sections:
  Food, Activity, Glucose Chart, Correlation Insight, and Recommendations. Each sub-section
  MUST be clearly headed.
- **FR-005**: The Food sub-section MUST include: identified food items, estimated
  nutritional breakdown (carbohydrates, proteins, fats, glycaemic index category), and a
  narrative of the expected blood glucose impact referencing the 70–140 mg/dL target range.
- **FR-006**: The Activity sub-section MUST include: activity type and intensity if provided,
  and an explanation of how that activity modulates the glucose response. If no activity was
  logged, the sub-section MUST display "No activity logged" rather than being absent.
- **FR-007**: The Glucose Chart sub-section MUST include: a glucose reading or estimated
  range at each CGM timing point provided, an explicit evaluation of each reading against
  the 70–140 mg/dL target range, and a descriptive label for the overall curve shape.
- **FR-008**: The Correlation Insight sub-section MUST provide explicit cause-and-effect
  statements linking identified food components and activity to specific observed glucose
  behaviours. Generic statements without reference to the session's actual data are not
  acceptable.
- **FR-009**: The Recommendations sub-section MUST contain at least one specific, actionable
  suggestion referencing the meal type or activity in the current session, with the goal of
  maintaining or returning glucose to the 70–140 mg/dL range.
- **FR-010**: The content of all five analysis sub-sections on the Miro card MUST be
  consistent with the analysis delivered in the Telegram message for the same session.
  The Miro card is a reformatted presentation of the same analysis, not a separate one.
- **FR-011**: If an image cannot be embedded (upload failure, unsupported format, file too
  large), the image slot MUST be replaced with a visible placeholder noting the image is
  unavailable. Card creation MUST NOT be blocked by a single image failure.
- **FR-012**: The Miro card MUST be created within 5 seconds of analysis completion under
  normal operating conditions, consistent with the existing SLO (Constitution VI).
- **FR-013**: A Miro card failure MUST NOT block or delay the Telegram analysis delivery.
  The two outputs are independent and Telegram delivery takes priority (existing FR-009
  from feature 001).
- **FR-014**: All images embedded in the Miro card MUST be tagged with the owning user's
  identifier at upload time. No user's images may appear on another user's card or be
  accessible via another user's card link.
- **FR-015**: The Miro card MUST display an anonymised user identifier (not the Telegram
  username, display name, or phone number) as a session label, consistent with the existing
  multi-user privacy requirement.
- **FR-016**: The AI analysis pipeline MUST produce richer, more detailed output sufficient
  to populate all five card sections. If the current analysis prompt produces insufficient
  detail for the card, the prompt MUST be updated to elicit the required depth — the card
  content requirements define the minimum analysis depth.

### Key Entities

- **EnhancedMiroCard**: A Miro card artefact replacing the basic card from feature 001.
  Contains an Input Data section (embedded images) and an Analysis section (five labelled
  sub-sections). References the source session and AI analysis. Belongs to one user.
- **CardImageSlot**: One embedded image position within a Miro card. Holds either a
  successfully uploaded food photo or CGM screenshot, or a placeholder if upload failed.
  Ordered: food photos first, CGM screenshots second.
- **CardAnalysisSection**: One of the five named sub-sections of the Analysis section
  (Food, Activity, Glucose Chart, Correlation Insight, Recommendations). Contains the
  formatted text content derived from the session's AI analysis.

---

## Multi-User Isolation & Cost Compliance

*Required for features that touch multi-user isolation or cost management (Constitution IV).*

**Multi-user isolation (Constitution II)**:
- Images are uploaded per-session under user-namespaced storage paths:
  `/users/{user_id}/sessions/{session_id}/miro-uploads/`.
- The Miro card creation call is scoped to the session's owning user — no cross-user
  card writing is permitted.
- The anonymised identifier shown on the card MUST NOT expose the user's Telegram identity.

**Cost impact (Constitution VII)**:
- This feature increases per-session AI token usage because the analysis prompt must
  produce richer, longer output to populate five card sections. The cost increase MUST be
  estimated before implementation and included in the plan.
- Image uploads to Miro consume bandwidth and potentially Miro API quota — rate limits
  and any associated costs MUST be assessed in the implementation plan.
- The $50/month hard cap remains binding. If the richer prompt materially increases
  monthly spend, per-session token budgeting (already required by Constitution VII) MUST
  be adjusted accordingly.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer opening the Miro board can identify all food photos and CGM
  screenshots from a session by looking at the card alone, without consulting Telegram or
  any other source — verified by visual inspection of 5 test sessions.
- **SC-002**: All five analysis sub-sections (Food, Activity, Glucose Chart, Correlation
  Insight, Recommendations) are present and contain substantive content (minimum 2
  sentences each) on 100% of generated cards where the session included at least one food
  photo and one CGM screenshot.
- **SC-003**: The Miro card is created and fully populated within 5 seconds of analysis
  completion for sessions containing up to 5 images total, under normal network conditions.
- **SC-004**: The Telegram analysis delivery time is unaffected by the enhanced Miro card
  creation — the 30-second SLO for Telegram delivery (SC-003 from feature 001) is not
  degraded.
- **SC-005**: Zero instances of one user's images appearing on another user's Miro card —
  verified by a cross-user access test with 3 different test users submitting concurrent
  sessions.
- **SC-006**: The Correlation Insight section on any card contains at least two explicit
  causal statements referencing specific foods or activities from the same session —
  verified by automated content validation against the session's raw input.
- **SC-007**: The Recommendations section on any card contains at least one
  session-specific suggestion (references the meal or activity by name) — verified by
  content inspection on 10 test sessions spanning different food types.
- **SC-008**: A single image upload failure does not prevent the card from being created
  or the remaining images from appearing — verified by injecting a simulated upload failure
  for one image in a multi-image session.

---

## Assumptions

- The Miro board API supports embedding images as first-class elements within a card frame;
  if the API only supports image links, this assumption is false and the feature scope must
  be revisited during planning.
- The AI analysis prompt used in feature 001 will be updated as part of this feature to
  produce the richer five-section output required by the card. This does not require a
  separate feature for "improved analysis" — the richer analysis is the same analysis,
  reformatted and extended.
- A session's photos and screenshots are accessible to the Miro card creation process after
  the AI analysis completes. Their storage paths follow the pattern established in feature
  001 (`/users/{user_id}/sessions/{session_id}/`).
- The anonymised user identifier shown on the card is a deterministic, consistent label
  derived from the user's internal identifier — not a one-time token. The same user always
  gets the same label on all their cards.
- The total number of images per session is bounded (assumption: maximum 10 photos + 4 CGM
  screenshots = 14 images). Unbounded image counts are not supported in this feature.
- This feature replaces the card created by feature 001 for all new sessions. Existing
  cards on the Miro board created by feature 001 are not retroactively updated — only
  cards created after this feature is deployed use the new design.
- Data sharing is out of scope for this feature. All card data defaults to private (the
  Miro board is pre-configured by the operator and is not user-scoped in the MVP).
