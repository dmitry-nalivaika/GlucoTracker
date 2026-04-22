# GlucoTrack Agentic Workflow Guide

## Overview

GlucoTrack is built using a structured multi-agent AI workflow. Every feature follows
the same pipeline from idea to production — no steps can be skipped.

Each "agent" is a Claude Code session that has been given a specific role. The role
defines what the agent is allowed to do, what it must not do, and what it must produce
before handing off to the next agent.

---

## The Four Agents

| Agent | Role | What it produces |
|---|---|---|
| **BA/Product Agent** | Define *what* to build | `spec.md` |
| **Developer Agent** | Build it | `plan.md`, `tasks.md`, code, PR |
| **Reviewer Agent** | Check it against the spec and constitution | PR review with BLOCKER/SUGGESTION labels |
| **QA/Test Agent** | Validate it works | QA report, test results, approval |

---

## The Full Workflow

```
1. You describe a feature
         ↓
2. BA/Product Agent  →  spec.md  →  you approve
         ↓
3. Developer Agent   →  plan.md + tasks.md + code + PR
         ↓
4. Reviewer Agent    →  BLOCKER? → back to Developer
         ↓ (no blockers)
5. QA/Test Agent     →  FAIL? → back to Developer
         ↓ (all pass)
6. CI Gate           →  lint + tests + coverage + security
         ↓ (green)
7. You merge PR      →  deploy fires automatically
         ↓
8. Azure production
```

---

## How to Invoke Each Agent

### Option A — One-command invocation (Claude Code skills)

Type these commands directly in Claude Code:

| Command | Agent invoked |
|---|---|
| `/ba-agent` | BA/Product Agent — write or refine a spec |
| `/dev-agent` | Developer Agent — plan, generate tasks, implement |
| `/reviewer-agent` | Reviewer Agent — review a PR |
| `/qa-agent` | QA/Test Agent — run quality gates and validate |

Each command loads the full agent role context automatically. You just add what you
need after the command:

```
/ba-agent Add a feature that lets users export their glucose history as CSV
/reviewer-agent Review PR #5
/qa-agent Validate PR #3 for feature 001
```

### Option B — GitHub PR auto-invocation

Post a comment on any open PR:

```
@reviewer-agent please review this PR
@qa-agent run QA checks on this PR
```

GitHub Actions will automatically:
1. Trigger a Claude Code session with the correct agent role loaded
2. Run the review or QA validation
3. Post the results back as a PR comment

> **Prerequisite**: `ANTHROPIC_API_KEY` must be set in GitHub repo secrets.
> See [setup instructions](#github-actions-setup) below.

---

## Step-by-Step: A Real Feature

### Phase 1 — Spec (BA/Product Agent)

1. Create a GitHub Issue describing the feature
2. In Claude Code, type:
   ```
   /ba-agent I want to add feature: [description]. GitHub Issue #N.
   ```
3. The agent writes `specs/NNN-feature/spec.md`
4. You review, answer any clarification questions
5. Commit the spec

**Handoff condition**: spec.md is committed, no [NEEDS CLARIFICATION] markers remain.

---

### Phase 2 — Implementation (Developer Agent)

1. In Claude Code, type:
   ```
   /dev-agent Implement the spec at specs/NNN-feature/spec.md
   ```
2. The agent:
   - Runs `/speckit-plan` → creates `plan.md`
   - Runs `/speckit-tasks` → creates `tasks.md`
   - Implements each task using TDD (test first, code second)
   - Commits after each task
3. When all tasks are done, the agent opens a PR

**Handoff condition**: PR is open, all local tests pass.

---

### Phase 3 — Review (Reviewer Agent)

**Option A** — In Claude Code:
```
/reviewer-agent Review PR #N
```

**Option B** — On GitHub, comment on the PR:
```
@reviewer-agent please review this PR
```

The Reviewer Agent:
- Reads the full PR diff
- Reads `spec.md`
- Labels issues as `BLOCKER:` or `SUGGESTION:`
- Approves only when all BLOCKERs are resolved

**If blockers found**: Developer Agent gets a new session, fixes them, pushes.
**If no blockers**: Reviewer approves.

**Handoff condition**: Reviewer has approved the PR.

---

### Phase 4 — QA Validation (QA/Test Agent)

**Option A** — In Claude Code:
```
/qa-agent Validate PR #N for feature specs/NNN-feature
```

**Option B** — On GitHub, comment on the PR:
```
@qa-agent run QA checks
```

The QA/Test Agent:
- Runs the full test suite (`pytest tests/ -v`)
- Checks coverage ≥ 80%
- Runs lint and security scan
- Executes manual acceptance scenarios from `spec.md`
- Tests cross-user data isolation explicitly
- Posts a QA Report as a PR comment

**If any gate fails**: QA blocks the PR; Developer fixes and resubmits.
**If all pass**: QA approves.

**Handoff condition**: QA has approved the PR.

---

### Phase 5 — Merge and Deploy (automated)

1. Confirm all three are green: CI Gate ✅, Reviewer ✅, QA ✅
2. You merge the PR on GitHub
3. GitHub Actions automatically:
   - Builds the Docker image
   - Deploys to staging
   - Runs smoke tests
   - Promotes to production

**No manual deployment steps needed.**

---

## Agent Hard Rules (never violate these)

| Rule | Who it applies to |
|---|---|
| No direct commits to `main` | Everyone |
| No merging your own PR | Developer Agent |
| No fixing code during review | Reviewer Agent |
| No fixing code during QA | QA/Test Agent |
| No implementing without a spec | Developer Agent |
| No spec without a GitHub Issue | BA/Product Agent |
| Tests must be written before implementation | Developer Agent |
| Every DB query must include `user_id` filter | Developer Agent |

---

## GitHub Actions Setup

To enable `@reviewer-agent` and `@qa-agent` triggers on PRs:

1. Go to your repo → **Settings → Secrets and variables → Actions**
2. Add secret: `ANTHROPIC_API_KEY` = your key from console.anthropic.com
3. The workflows in `.github/workflows/agent-reviewer.yml` and
   `.github/workflows/agent-qa.yml` are already configured

Once the secret is set, posting `@reviewer-agent` or `@qa-agent` in any PR comment
will automatically trigger the corresponding agent.

---

## File Structure Reference

```
.claude/
├── agents/                    # Agent role definitions (full instructions)
│   ├── ba-product-agent.md
│   ├── developer-agent.md
│   ├── reviewer-agent.md
│   └── qa-test-agent.md
└── skills/                    # One-command invocation shortcuts
    ├── ba-agent/SKILL.md
    ├── dev-agent/SKILL.md
    ├── reviewer-agent/SKILL.md
    └── qa-agent/SKILL.md

.github/
├── workflows/
│   ├── ci.yml                 # Automated CI on every PR
│   ├── deploy.yml             # Auto-deploy on merge to main
│   ├── agent-reviewer.yml     # @reviewer-agent GitHub trigger
│   └── agent-qa.yml          # @qa-agent GitHub trigger
└── pull_request_template.md  # PR checklist

.specify/
└── memory/
    └── constitution.md        # Non-negotiable rules all agents follow

specs/
└── NNN-feature-name/
    ├── spec.md                # BA/Product Agent output
    ├── plan.md                # Developer Agent output
    ├── tasks.md               # Developer Agent output
    └── checklists/
        └── requirements.md
```

---

## Troubleshooting

**"CI Gate is failing but I don't know why"**
→ Click the failing CI Gate job in GitHub Actions, expand the step that failed.

**"Reviewer posted a BLOCKER but I don't understand it"**
→ Start a Developer Agent session: `/dev-agent Fix the BLOCKER in PR #N: [paste the blocker text]`

**"QA is failing but tests pass locally"**
→ Check that your test environment matches CI (Python version, env vars).
   Run `pytest tests/ -v --tb=short` locally to see the same output as CI.

**"@reviewer-agent comment does nothing"**
→ Check that `ANTHROPIC_API_KEY` is set in repo secrets and the workflow is enabled
   under Actions tab.
