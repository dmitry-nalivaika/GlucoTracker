# Contract: /language Bot Command

**Feature**: 003-russian-language-support
**Type**: Telegram bot command

---

## Command Schema

```
/language <code>
```

| Parameter | Type   | Required | Values               | Description                   |
|-----------|--------|----------|----------------------|-------------------------------|
| `code`    | string | yes      | `"en"`, `"ru"`       | BCP-47-style language code    |

---

## Behaviour Contract

### Success path — valid language code

**Input**: `/language ru`
**Precondition**: User exists in DB (any language_code, including NULL)
**Effect**:
- `users.language_code` set to `"ru"` for this user
- All subsequent bot messages to this user are in Russian
- `context.user_data["lang"]` updated to `"ru"` (in-session cache)

**Response** (MarkdownV2, in the **new** language):
```
✅ Язык изменён на: *Русский*
```
(English confirmation if switching to English: `✅ Language changed to: *English*`)

---

### Error path — unsupported language code

**Input**: `/language xx` (any code not in SUPPORTED set)
**Effect**: No DB change; user's current language unchanged
**Response** (MarkdownV2, in the user's **current** language — before the attempted change):
```
⚠️ Unsupported language code: xx
Supported languages: en (English), ru (Русский)
Usage: /language <code>
```

---

### Error path — missing argument

**Input**: `/language` (no code)
**Effect**: No DB change
**Response** (in user's current language):
```
⚠️ Please specify a language code.
Supported languages: en (English), ru (Русский)
Usage: /language <code>
```

---

## Timing Constraint

- Bot acknowledgement MUST arrive within 2 seconds (Constitution VI SLO)
- DB write is a simple UPDATE on a single row — negligible latency

---

## Isolation Constraint

- Language change affects ONLY the requesting user (FR-010, Constitution II)
- No shared state is mutated
- Concurrent `/language` commands from different users must not interfere

---

## Test Scenarios (from spec)

| # | Input | Precondition | Expected response language | DB effect |
|---|-------|--------------|---------------------------|-----------|
| 1 | `/language ru` | lang=NULL (default) | Russian | `language_code = "ru"` |
| 2 | `/language en` | lang=`"ru"` | English | `language_code = "en"` |
| 3 | `/language xx` | lang=`"en"` | English (current) | no change |
| 4 | `/language` | lang=`"ru"` | Russian (current) | no change |
| 5 | Two concurrent `/language` | users A (en), B (ru) | Each their own | isolated |
