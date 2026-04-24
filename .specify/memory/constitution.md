<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.0.1  — PATCH: enforce no-direct-commits-to-main
Added sections: none
Modified principles:
  - Git Workflow Rules: added NON-NEGOTIABLE callout block explicitly prohibiting
    direct commits to `main` under all circumstances (including bugfixes/hotfixes);
    expanded PR lifecycle step 1 to require a feature branch always.
  - Previous version (1.0.0) already contained the rule but it was insufficiently
    prominent; this amendment makes it unambiguous and impossible to miss.

---

Version change: (blank template) → 1.0.0  — INITIAL RATIFICATION
Added sections:
  - I.  Vision
  - II. Multi-User Architecture & Data Isolation (NON-NEGOTIABLE)
  - III. Technology Stack & Rationale
  - IV. Feature-Based Delivery Process (NON-NEGOTIABLE)
  - V.  Code Quality & Testing Standards (NON-NEGOTIABLE)
  - VI. UX Consistency
  - VII. Cost Management ($50/month Hard Cap) (NON-NEGOTIABLE)
  - Agent Roles & Responsibilities
  - Git Workflow Rules
  - CI/CD Pipeline Definition
  - Documentation Standards
  - Governance
Modified principles: none (initial ratification)
Removed sections: none
Templates:
  - .specify/templates/plan-template.md    ✅ already contains "Constitution Check" gate
  - .specify/templates/spec-template.md    ✅ no changes required
  - .specify/templates/tasks-template.md   ✅ no changes required
Deferred TODOs:
  - TODO(AZURE_SERVICES): Exact Azure services (App Service vs Container Apps vs Functions)
    not yet decided — to be resolved before first infrastructure feature.
  - TODO(AUTH_PROVIDER): Authentication provider (Azure AD B2C / Auth0 / custom JWT)
    not yet decided — to be resolved before identity/auth feature.
  - TODO(STORAGE_ENGINE): Data storage solution (Azure SQL / CosmosDB / Blob)
    not yet decided — to be resolved before persistence feature.
  - TODO(CGM_PARSING): CGM screenshot parsing approach (OCR vs structured API)
    not yet decided — to be resolved during CGM integration feature.
  - TODO(SESSION_GROUPING): Telegram session grouping logic (time window vs manual trigger)
    not yet decided — to be resolved during Telegram MVP feature.
  - TODO(TELEGRAM_IDENTITY): Telegram ↔ platform account linking strategy
    not yet decided — to be resolved during identity/auth feature.
  - TODO(GROUP_UI_SCOPE): Group/cohort management UI — MVP or post-MVP scope TBD.
-->

# GlucoTrack Constitution

## Core Principles

### I. Vision

GlucoTrack is a mobile-first, AI-powered platform for personal glucose level analysis.
The system correlates food intake, physical activity, and continuous glucose monitor (CGM)
readings to deliver personalised insights that help users maintain healthy glucose levels.

---

### II. Multi-User Architecture & Data Isolation (NON-NEGOTIABLE)

**This principle is non-negotiable. No exception or deferral is permitted.**

The system MUST be multi-tenant from the first line of production code.

**Isolation rules**:
- Every database query MUST include a `user_id` predicate at the data-access layer.
  A query that runs without user context is a critical bug, not a minor violation.
- File storage paths MUST follow the pattern `/users/{user_id}/sessions/{session_id}/…`.
  No flat or shared storage paths are permitted for user-generated content.
- Data sharing MUST be implemented via an Access Control List (ACL) table.
  Data MUST NOT be duplicated into a shared namespace to implement sharing.
- Revoking access MUST take effect immediately with no grace period or cached exposure.
- All sharing grant/revoke actions MUST be written to an immutable audit log.

**Data sharing levels** (opt-in only; private is the default):

| Level | Description |
|---|---|
| Private (default) | Visible to owner only |
| Shared with specific users | Owner grants named users read-only access |
| Shared with a group | Owner joins/creates a care team or study cohort |
| Public (future) | Anonymised data for community insights |

**Shared access is read-only by default.** Write or comment access is a post-MVP extension
and MUST be explicitly scoped in its own feature specification.

**Authentication**:
- In the Telegram MVP, the user identity is the Telegram user ID.
- All stored artefacts (photos, screenshots, sessions, AI analysis) MUST be tagged with the
  owning user's ID at write time.
- TODO(AUTH_PROVIDER): Formal authentication provider selection is deferred.

---

### III. Technology Stack & Rationale

**Choices are binding. Changes require a constitution amendment.**

| Layer | Technology | Rationale |
|---|---|---|
| Backend | Python | Broad AI/ML ecosystem; strong Azure SDK support |
| Frontend (future) | React or Vue.js | Component-based; large talent pool |
| Cloud | Microsoft Azure | Enterprise compliance; integrated cost management |
| AI/ML | Anthropic Claude API (vision + text) | Best-in-class multimodal; structured JSON output |
| Version control | GitHub | Industry standard; native GitHub Actions CI/CD |
| CI/CD | GitHub Actions → Azure | Tight VCS integration; free tier covers MVP workload |
| MVP input channel | Telegram Bot API | Zero-app-install friction; rapid iteration |
| MVP visualisation | Miro Board API | No-code canvas; shareable; replaceable |

**Architecture constraints**:
- Input channels (Telegram, future mobile app) MUST be implemented behind an interface/
  adapter so the core domain logic has no dependency on the channel.
- Visualisation layers (Miro, future dashboard) MUST be pluggable via an output adapter.
- Storage drivers (SQL, Blob, CosmosDB) MUST be abstracted behind a repository interface.
- The Claude API integration MUST be isolated in a dedicated AI service module; domain
  code MUST NOT call Claude directly.

**Deferred decisions**: TODO(AZURE_SERVICES), TODO(STORAGE_ENGINE) — see Sync Impact Report.

---

### IV. Feature-Based Delivery Process (NON-NEGOTIABLE)

**All development MUST follow this process. No exceptions.**

```
GitHub Issue + Spec (spec.md)
        ↓
Feature branch created
        ↓
Implementation plan (plan.md) + Constitution Check gate
        ↓
Tasks generated (tasks.md)
        ↓
Developer Agent implements
        ↓
Pull Request opened
        ↓
Quality Gates (all must pass):
  ├── Automated tests: unit + integration (green)
  ├── Code coverage threshold met
  ├── Reviewer Agent check (against spec + constitution)
  └── QA Agent validation
        ↓
PR merged to main
        ↓
Azure deployment triggered automatically
```

**Hard rules**:
- Direct commits to `main` are FORBIDDEN.
- A PR MUST NOT be merged while any quality gate is failing.
- Every feature MUST start with a GitHub Issue and a `spec.md` document.
- The Constitution Check in `plan.md` MUST be completed and all gates passed before
  Phase 0 research begins.
- Features that touch multi-user isolation, cost management, or data sharing MUST include
  an explicit section in their spec documenting compliance with Principles II and VII.

---

### V. Code Quality & Testing Standards (NON-NEGOTIABLE)

**Test discipline**:
- Unit tests and integration tests MUST be written and verified to fail **before**
  the implementation code that makes them pass is written (TDD/Red-Green-Refactor).
- Merging code with no test coverage for a new feature or a fixed bug is FORBIDDEN.
- Minimum code coverage threshold: **80% line coverage** for all new code.
  The threshold MUST be enforced in CI and will block merges.
- Contract tests MUST exist for every public API endpoint and every Claude API call schema.

**Code standards**:
- Python backend MUST pass `ruff` (linting) and `black` (formatting) checks in CI.
- Type annotations MUST be present on all public functions and class methods.
- No `print()` debugging statements in committed code; use structured logging only.
- Secrets MUST NOT appear in source code. Use environment variables or Azure Key Vault.
- SQL queries and ORM calls MUST use parameterised inputs — SQL injection is a blocker.
- All user-supplied input (Telegram messages, photo metadata) MUST be validated at the
  system boundary before processing.

**Review standards**:
- Every PR requires at least one Reviewer Agent pass.
- Reviewer Agent MUST explicitly verify: spec compliance, principle compliance, test
  coverage, and absence of hardcoded credentials or SQL-injection vectors.
- Comments labelled `BLOCKER:` in a review MUST be resolved before merge.

---

### VI. UX Consistency

**Performance targets** (these are contractual SLOs, not aspirational):

| Operation | Target |
|---|---|
| Telegram bot response (acknowledgement) | < 2 seconds |
| AI session analysis (full response) | < 30 seconds |
| API endpoint p95 latency (non-AI calls) | < 500 ms |
| Miro board card creation | < 5 seconds |

**UX consistency rules**:
- Error messages returned to the user MUST be human-readable and actionable;
  raw stack traces MUST NOT be surfaced to the user.
- All timestamps stored and displayed MUST include timezone offset or be stored as UTC
  with explicit conversion at display time.

---

### VII. Cost Management — $50/Month Hard Cap (NON-NEGOTIABLE)

**This principle is non-negotiable. Exceeding $50/month is a system failure.**

- Total monthly spend across ALL Azure services + Anthropic API MUST NOT exceed **$50 USD**.
- An Azure Budget Alert MUST be configured at **$40** (80% threshold) to send an email
  notification to the project owner.
- A second alert MUST trigger at **$48** (96% threshold) and MUST automatically suspend
  non-critical Azure resources (e.g., scale compute to zero, pause non-essential services).
- The Anthropic API integration MUST implement per-user rate limiting and per-session
  token budgeting to prevent runaway costs from a single session.
- Every new Azure service added to the stack MUST include a cost estimate in its feature
  spec, with an analysis showing the estimated impact on the monthly budget.
- Infrastructure-as-Code (IaC) MUST enforce auto-scale-down policies; persistent "always-on"
  resources that have cost-free equivalents are FORBIDDEN without documented justification.

---

## Agent Roles & Responsibilities

Each Claude Code agent session operates in exactly one of these roles.
Mixing roles in a single session is FORBIDDEN.

| Agent | Role | Responsibilities |
|---|---|---|
| **BA/Product Agent** | Specification | Author `spec.md`; define user stories with acceptance criteria; confirm scope with stakeholder; flag open questions |
| **Developer Agent** | Implementation | Implement tasks from `tasks.md`; write tests (TDD); keep commits atomic; respect feature branch |
| **Reviewer Agent** | Code Review | Review PR against `spec.md` and this constitution; label blocking issues; verify test coverage; approve or request changes |
| **QA/Test Agent** | Quality Assurance | Run full test suite; validate coverage thresholds; run manual acceptance scenarios from spec; block merge on failure |

**Handoff protocol**:
1. BA/Product Agent produces `spec.md` → hands off to Developer Agent.
2. Developer Agent produces implementation + `plan.md` + `tasks.md` → opens PR.
3. PR triggers Reviewer Agent and QA/Test Agent in parallel.
4. Only after both approve does the PR merge to `main`.

**No agent may skip a handoff step.** If a step cannot be completed, the agent MUST
surface a blocker rather than proceeding unilaterally.

---

## Git Workflow Rules

> **NON-NEGOTIABLE: NO DIRECT COMMITS TO `main`**
> Every change — including bug fixes, typos, and hotfixes — MUST go through a
> feature branch and a Pull Request. There are zero exceptions. An agent that
> commits directly to `main` has violated the constitution.

- **Branch naming**: `{issue-number}-{kebab-case-description}`
  (e.g., `12-telegram-session-grouping`).
- **Base branch**: All feature branches MUST branch from `main`.
- **Commit messages**: Conventional Commits format REQUIRED:
  `type(scope): description` — types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`.
- **Commit size**: Each commit MUST represent one logical change.
  Mixing unrelated changes in a single commit is FORBIDDEN.
- **Direct commits to `main`**: FORBIDDEN under all circumstances, including
  bugfixes, hotfixes, typo corrections, and post-PR-merge follow-ups.
- **Force push**: Force-pushing to `main` is FORBIDDEN under all circumstances.
- **Merge strategy**: Squash-merge to `main` for feature branches to keep history readable.
- **PR lifecycle**:
  1. Create a feature branch from `main` — always, no exceptions.
  2. Open PR as draft during development.
  3. Mark ready-for-review only when all local tests pass.
  4. All quality gates must pass before merge.
  5. Delete the feature branch after merge.
- **No WIP commits on `main`**: `main` MUST always be in a deployable state.

---

## CI/CD Pipeline Definition

Every PR MUST pass the following pipeline stages in order. Any stage failure blocks merge.

```
Stage 1: Lint & Format
  ├── ruff check src/ tests/
  └── black --check src/ tests/

Stage 2: Type Check
  └── mypy src/

Stage 3: Unit Tests
  ├── pytest tests/unit/ -v
  └── Coverage report generated (fail if < 80%)

Stage 4: Integration Tests
  └── pytest tests/integration/ -v

Stage 5: Contract Tests
  └── pytest tests/contract/ -v

Stage 6: Security Scan
  └── bandit -r src/ (fail on HIGH severity findings)

Stage 7: Cost Guard (infrastructure PRs only)
  └── terraform plan + cost estimation validation

Stage 8: Reviewer Agent Check
  └── AI review of spec compliance and principle compliance
```

**Post-merge deployment pipeline** (triggered on merge to `main`):

```
Build → Push container image to Azure Container Registry
     → Deploy to staging environment
     → Run smoke tests against staging
     → On success: promote to production
     → On failure: roll back automatically; alert project owner
```

**Deployment is fully automated.** Manual deployments to production are FORBIDDEN.

---

## Documentation Standards

Three documentation layers MUST be maintained concurrently with code changes.
A PR that adds or changes functionality without updating relevant docs MUST be rejected.

### 1. Developer Documentation (`docs/developer/`)
- Architecture overview with component diagram.
- Local development setup guide — sufficient for a new developer to run the system
  from zero with a single `make dev` or equivalent command.
- API reference for all backend endpoints (auto-generated from OpenAPI spec preferred).
- Data model reference.
- Environment variable reference with descriptions and example values.

### 2. User Documentation (`docs/user/`)
- End-to-end guide: how to start a session, log food, add CGM screenshots, log activity.
- How to read and act on AI analysis output.
- How to use the data sharing features.
- FAQ covering common issues.

### 3. Extension & Contribution Guide (`docs/extension/`)
- How to add a new input channel (replacing or adding alongside Telegram bot).
- How to add a new visualisation layer (replacing or adding alongside Miro board).
- How to extend the AI analysis pipeline (new prompts, new data sources).
- How to run the full test suite locally.

**Documentation quality gate**: Docs MUST be reviewed as part of each PR. Stale docs
that contradict current behaviour are treated as bugs.

---

## Governance

This constitution supersedes all other project practices, conventions, and agent
instructions. When a conflict exists between this document and any other instruction,
this document wins.

**Amendment process**:
1. Raise a GitHub Issue with label `constitution-amendment` describing the proposed change
   and justification.
2. The BA/Product Agent authors a diff against this document.
3. A Reviewer Agent reviews the diff for internal consistency and downstream impact.
4. The project owner approves the amendment.
5. `LAST_AMENDED_DATE` and `CONSTITUTION_VERSION` MUST be updated in the same commit.
6. All dependent templates (plan, spec, tasks) MUST be reviewed for propagation impact.

**Versioning policy**:
- **MAJOR** bump: removal or redefinition of a non-negotiable principle.
- **MINOR** bump: new principle or section added; material expansion of existing guidance.
- **PATCH** bump: clarifications, wording fixes, non-semantic refinements.

**Compliance review**:
- The Reviewer Agent MUST verify constitution compliance on every PR.
- A quarterly review of this document is RECOMMENDED to retire deferred TODOs as
  open questions get resolved.
- Non-negotiable principles (II, IV, V, VII) MUST NOT be waived under any circumstances,
  including time pressure or cost pressure.

**Version**: 1.0.1 | **Ratified**: 2026-04-17 | **Last Amended**: 2026-04-24
