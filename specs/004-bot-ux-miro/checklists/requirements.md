# Requirements Checklist — 004-bot-ux-miro

## Spec Quality Gates

- [ ] All user stories have Given/When/Then acceptance scenarios
- [ ] All FRs are testable and technology-agnostic
- [ ] Success criteria are measurable (no vague statements)
- [ ] Assumptions section documents all defaults taken
- [ ] GitHub Issue #7 is linked in the spec
- [ ] No more than 3 [NEEDS CLARIFICATION] markers remain

## Functional Coverage

### Group A — Telegram Bot UX
- [ ] FR-001: Start button visible on initial screen
- [ ] FR-002: Done and Cancel as persistent first-screen buttons
- [ ] FR-003: CGM timing buttons as single-tap inline buttons
- [ ] FR-004: Bot startup broadcast to all known users
- [ ] FR-005: Bot shutdown broadcast before process exits
- [ ] FR-006: Guided first message after Start
- [ ] FR-007: Step-by-step confirmation and next-step prompts
- [ ] FR-008: Pre-submission summary before finalising
- [ ] FR-009: Graceful handling of unexpected input types
- [ ] FR-010: Cancel discards session and returns to Start state
- [ ] FR-011: Done rejected if no food photo submitted

### Group B — Miro Card Enhancements
- [ ] FR-012: Photos in single horizontal row (food first, then CGM)
- [ ] FR-013: RAG status indicator with Green/Amber/Red/Grey thresholds
- [ ] FR-014: RAG indicator accompanied by summary sentence
- [ ] FR-015: Executive Summary block before five detail sections
- [ ] FR-016: Appreciation block with context-aware encouragement
- [ ] FR-017: Summary and Appreciation visually distinct and positioned first
- [ ] FR-018: New layout applies only to cards created after deployment

## Constitution Compliance
- [ ] All data scoped by user_id (Constitution II)
- [ ] Cost impact estimated in spec (Constitution VII)
- [ ] No tech-specific implementation language in requirements
- [ ] Glucose target range (70–140 mg/dL) referenced where relevant
- [ ] Data sharing defaults to private

## Handoff Readiness
- [ ] No [NEEDS CLARIFICATION] markers remaining
- [ ] All user stories have independent tests defined
- [ ] Spec reviewed and approved by stakeholder
- [ ] Ready to hand off to Developer Agent (`/dev-agent`)
