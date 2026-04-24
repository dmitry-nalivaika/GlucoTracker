# AI Prompt Contract: 004 — Extended Session Analysis Response

**Extends**: `specs/001-telegram-mvp-session-logging/contracts/ai-analysis-schema.md`

## New Fields Added to `SESSION_ANALYSIS_SYSTEM_PROMPT`

The following two fields are appended to the JSON response schema:

```json
{
  "executive_summary": "<string: 2–3 sentences summarising the session — food consumed, glucose response, and one key insight>",
  "encouragement": "<string: 1 sentence of positive appreciation or encouragement for the user>"
}
```

### Validation Rules

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `executive_summary` | string | yes (new) | 2–3 sentences; references food and glucose; language matches user's language setting |
| `encouragement` | string | yes (new) | 1 sentence; positive/encouraging tone; language matches user's language setting |

### Backward Compatibility

- Existing sessions with `raw_response` that do not contain `executive_summary` or
  `encouragement` MUST be handled gracefully in `miro_service._build_section_text`.
- Fallback: use i18n strings `miro_summary_unavailable` and `miro_encouragement_default`.

### Contract Test Requirement

The contract test in `tests/contract/test_ai_contract.py` must assert that:
- `executive_summary` key is present in a parsed AI response mock
- `encouragement` key is present in a parsed AI response mock
- Both are non-empty strings

### Prompt Addition (exact wording)

Append to `SESSION_ANALYSIS_SYSTEM_PROMPT` after the closing `}`:

```
  "executive_summary": "<2-3 sentences: food consumed, glucose response observed, key insight for this session>",
  "encouragement": "<1 sentence of positive feedback or encouragement for the user>"
```
