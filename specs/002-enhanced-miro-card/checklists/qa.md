# QA Acceptance Checklist: Enhanced Miro Board Card with Embedded Photos and Rich AI Analysis

**Purpose**: Validate acceptance criteria quality and test coverage completeness for QA gate
**Created**: 2026-04-23
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 Are acceptance scenarios defined for all five analysis sub-sections (Food, Activity, Glucose Chart, Correlation Insight, Recommendations)? [Completeness, Spec §FR-004]
- [ ] CHK002 Are requirements for image ordering (food photos before CGM screenshots) explicitly stated and testable? [Completeness, Spec §FR-002]
- [ ] CHK003 Are the fallback behaviors for each section when AI output is empty or malformed explicitly specified? [Completeness, Spec §Edge Cases]
- [ ] CHK004 Is the anonymised user identifier format defined with enough specificity to be consistently verified across test sessions? [Clarity, Spec §FR-015]
- [ ] CHK005 Are requirements for the Miro card's two-section visual layout (Input Data vs Analysis) defined with enough precision to distinguish them in automated tests? [Clarity, Spec §FR-003]

## Acceptance Criteria Quality

- [ ] CHK006 Is SC-002 ("minimum 2 sentences each") measurable and consistently verifiable across all five sections? [Measurability, Spec §SC-002]
- [ ] CHK007 Does each user story acceptance scenario have a corresponding test (unit or integration) that exercises it independently? [Coverage, Spec §US1–US5]
- [ ] CHK008 Are the 70–140 mg/dL boundary conditions explicitly required in Food, Glucose Chart, and Recommendations sections — or only in some? [Consistency, Spec §FR-005, §FR-007, §FR-009]
- [ ] CHK009 Is SC-006 ("at least two causal statements") verifiable by automated content inspection, or does it require manual review? [Measurability, Spec §SC-006]
- [ ] CHK010 Is the requirement that Telegram and Miro card content be "consistent" (FR-010) defined with enough precision to be falsifiable — i.e., what constitutes an inconsistency? [Clarity, Spec §FR-010]

## Scenario Coverage

- [ ] CHK011 Are acceptance scenarios defined for sessions containing zero CGM screenshots (Glucose Chart fallback)? [Coverage, Spec §Edge Cases]
- [ ] CHK012 Are requirements defined for sessions containing the maximum bounded image count (10 food + 4 CGM = 14 images)? [Coverage, Spec §Assumptions]
- [ ] CHK013 Is the scenario where all images fail to upload addressed in acceptance criteria (card still created with all 5 sections)? [Coverage, Spec §FR-011]
- [ ] CHK014 Are concurrent multi-user session scenarios (SC-005: 3 users submitting at the same time) covered by automated isolation tests rather than manual inspection only? [Coverage, Spec §SC-005]
- [ ] CHK015 Is the retry behavior for Miro card creation (FR-009 from feature 001) specified with enough detail to verify it doesn't impact Telegram SLO? [Coverage, Spec §FR-013]

## Multi-User Isolation Requirements

- [ ] CHK016 Is the requirement that images be "tagged with the owning user's identifier at upload time" (FR-014) verifiable at the API request level, not just storage level? [Measurability, Spec §FR-014]
- [ ] CHK017 Are storage path requirements for Miro-uploaded images consistent with Constitution II pattern (`/users/{user_id}/sessions/{session_id}/`)? [Consistency, Spec §Multi-User Isolation]
- [ ] CHK018 Is the cross-user card access prevention tested at both the DB query level and the Miro API call level? [Coverage, Spec §FR-014]

## Non-Functional Requirements

- [ ] CHK019 Is the 5-second SLO (SC-003) for cards containing up to 5 images defined as a hard gate or a soft target? [Clarity, Spec §SC-003, §FR-012]
- [ ] CHK020 Are token budget requirements for the richer AI prompt (Constitution VII) specified in the plan with enough precision to verify the $50/month cap is not at risk? [Coverage, Spec §Cost Impact]
- [ ] CHK021 Is the Miro API rate limit impact of uploading up to 14 images per session addressed in requirements? [Gap, Spec §Cost Impact]

## Edge Case Coverage

- [ ] CHK022 Is the requirement for the Activity section fallback ("No activity logged") specified as a mandatory display string or just described as "something to show"? [Clarity, Spec §FR-006]
- [ ] CHK023 Are requirements defined for what happens when the AI analysis produces a gi_category value outside the allowed enum (low/medium/high/null)? [Gap, Spec §FR-005]
- [ ] CHK024 Is the CGM "unreadable" advisory (US3 AC4) specified to always appear even if glucose_curve_json is empty, or only when cgm_parseable is explicitly false? [Clarity, Spec §US3]

## Notes

- CHK010 is flagged as the highest-risk ambiguity: FR-010 ("consistent with Telegram message") is hard to falsify automatically without content diffing logic.
- CHK009 and CHK006 may require manual spot-check for content quality since automated checks can only verify structure, not substance.
- CHK019 should be confirmed with the developer: is the 5s SLO enforced in CI or only observed in production?
