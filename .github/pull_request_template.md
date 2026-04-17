## Summary

<!-- 1–3 bullet points describing what this PR does and why -->

-

## Linked Spec & Issue

- **GitHub Issue**: #
- **Spec**: `specs/NNN-feature-name/spec.md`
- **Feature branch**: `NNN-feature-name`

---

## BA/Product Agent — Spec Compliance

> Reviewer Agent: verify each item against `spec.md` before approving.

- [ ] All functional requirements (FR-NNN) addressed or explicitly deferred with justification
- [ ] All user story acceptance scenarios covered by tests or demonstrable behaviour
- [ ] No scope creep — changes are bounded by the spec
- [ ] Key entities match the data model defined in the spec

---

## Developer Agent — Implementation Checklist

- [ ] Tests written **before** implementation (TDD — red before green)
- [ ] Unit tests present for all new functions/methods
- [ ] Integration tests present for all new API endpoints or service interactions
- [ ] Contract tests present for all external-facing interfaces (API, Claude API calls)
- [ ] Code coverage ≥ 80% on new code (verified by CI report)
- [ ] No `print()` statements — structured logging used throughout
- [ ] No hardcoded secrets, credentials, or API keys
- [ ] All user-supplied inputs validated at system boundaries
- [ ] SQL/ORM queries use parameterised inputs (no string concatenation)

---

## Constitution Compliance (NON-NEGOTIABLE)

> Any unchecked item here is a **BLOCKER** — PR MUST NOT merge.

- [ ] **Principle II** — Every DB query scoped by `user_id`; storage paths follow `/users/{user_id}/sessions/...`
- [ ] **Principle II** — No cross-user data access possible under any code path
- [ ] **Principle IV** — Feature started from a GitHub Issue + spec.md (not ad-hoc)
- [ ] **Principle V** — Tests written first; coverage ≥ 80%; no raw stack traces exposed to users
- [ ] **Principle VII** — No new always-on Azure resources without cost estimate in spec; budget alerts unaffected

---

## Reviewer Agent Sign-off

- [ ] Spec compliance verified (all FR-NNN checked above)
- [ ] Constitution compliance verified (all non-negotiable items above)
- [ ] No `BLOCKER:` comments remaining unresolved
- [ ] Code is readable, minimal, and free of unnecessary abstractions

**Reviewer**: <!-- @mention or "Reviewer Agent session YYYY-MM-DD" -->

---

## QA/Test Agent Sign-off

- [ ] Full test suite passes locally (`pytest tests/ -v`)
- [ ] Coverage threshold met (`--cov-fail-under=80`)
- [ ] Manual acceptance scenarios from spec.md executed and passing
- [ ] No regressions introduced in previously passing tests

**QA**: <!-- @mention or "QA Agent session YYYY-MM-DD" -->

---

## Post-merge

- [ ] Deployment to staging verified (GitHub Actions deploy job green)
- [ ] Smoke tests passing on staging
- [ ] Azure cost budget unaffected (no spike in projected spend)
