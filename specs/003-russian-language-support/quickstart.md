# Quickstart: Testing Russian Language Support (Feature 003)

**Branch**: `003-russian-language-support`

---

## Manual Test Scenarios

### Scenario A — Basic language switch (US1)

1. Start a fresh bot session (or use `/start`)
2. Send `/language ru`
3. **Expected**: Bot replies in Russian confirming the change
4. Send any other command (e.g. `/status`)
5. **Expected**: Response is in Russian
6. Close conversation, start a new session
7. Send `/status` again
8. **Expected**: Still in Russian — preference persisted

---

### Scenario B — Switch back to English (US1)

1. (User already has Russian set — see Scenario A)
2. Send `/language en`
3. **Expected**: Bot replies in English confirming the change
4. Send `/status`
5. **Expected**: Response is in English

---

### Scenario C — Invalid language code (US1)

1. Send `/language de`
2. **Expected**: Bot replies in current language (English) listing supported codes
3. `language_code` in DB unchanged

---

### Scenario D — AI analysis in Russian (US2)

1. Set language to Russian: `/language ru`
2. Send a food photo → confirm it's a food photo
3. Send a CGM screenshot → set timing label
4. Send `/done`
5. **Expected**: "Analysis in progress..." message in Russian
6. **Expected**: Full analysis delivered in Russian — all five sections

---

### Scenario E — Concurrent users (US1 + US2)

1. Open two bot sessions (different Telegram accounts)
2. User A: `/language en`; User B: `/language ru`
3. Both complete sessions simultaneously
4. **Expected**: User A receives English analysis; User B receives Russian analysis
5. **Expected**: No cross-contamination

---

### Scenario F — Language change mid-session (edge case)

1. Send a food photo (session open)
2. Send `/language ru` (language changes mid-session)
3. Send a CGM screenshot
4. Send `/done`
5. **Expected**: Analysis delivered in Russian (new language takes effect for new messages)

---

## Automated Test Locations

| Test file | What it covers |
|---|---|
| `tests/unit/test_i18n.py` | `t()` helper — key lookup, fallback, format kwargs |
| `tests/unit/test_formatters.py` | All formatter functions with `lang="ru"` |
| `tests/unit/test_language_command.py` | `/language` handler — valid, invalid, missing arg |
| `tests/integration/test_language_flow.py` | Full flow: set language, complete session, verify analysis lang |
| `tests/contract/test_language_command_contract.py` | Command schema: valid codes, error responses |

---

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v                         # all tests
pytest tests/unit/test_i18n.py -v        # i18n catalogue only
pytest tests/integration/test_language_flow.py -v   # integration
```
