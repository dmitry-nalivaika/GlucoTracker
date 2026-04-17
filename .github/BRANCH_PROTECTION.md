# Branch Protection Setup

Branch protection requires GitHub Pro or a public repository.
Once either condition is met, run this command to enforce the rules:

```bash
gh api repos/dmitry-nalivaika/GlucoTracker/branches/main/protection \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  --field required_status_checks='{"strict":true,"contexts":["CI Gate"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"required_approving_review_count":1}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false
```

## What this enforces

- No direct push to `main` — all changes must come via PR
- PR requires 1 approving review (stale reviews dismissed on new push)
- CI Gate job must pass before merge is allowed
- Force-push to `main` is blocked
- `main` branch cannot be deleted
