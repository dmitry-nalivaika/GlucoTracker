# Research: Russian Language Support (Feature 003)

**Branch**: `003-russian-language-support` | **Date**: 2026-04-24

---

## Decision 1 — Translation Mechanism

**Decision**: A nested dict catalogue in `src/glucotrack/bot/i18n.py`, accessed via a `t(key, lang, **kwargs) -> str` helper.

**Rationale**: `gettext` adds a compile step and toolchain complexity. `Babel`/`fluent.python` are designed for grammatical complexity and external formats. A plain dict is zero-dependency, `mypy --strict`-compatible, trivially extensible (new language = new key in the dict), and MarkdownV2-safe since translated strings are stored pre-escaped alongside their English counterparts.

**Alternatives considered**:
- `gettext` (stdlib) — `.po`/`.mo` files + `msgfmt` compile step; unjustified for 2 languages and ~20 strings
- `Babel` — oriented at date/number locale; no benefit here
- `fluent.python` — designed for gender/plural rules; overkill for English + Russian flat messages
- `if/else` per formatter — scatters Russian strings across every file, violates FR-009

---

## Decision 2 — Threading `lang` Through Formatters

**Decision**: Add `lang: str = "en"` as a keyword argument to every public formatter function. Handlers resolve `lang` once per request (from `context.user_data["lang"]`, populated from the DB on first access) and pass it to every formatter call.

**Rationale**: Per-user isolation (FR-010) requires stateless propagation — a function argument is the only approach trivially verifiable at call sites. Global state or `contextvars` would make cross-user contamination invisible. The `context.user_data["lang"]` cache avoids a DB round-trip per message.

**Alternatives considered**:
- Global language variable — fails FR-010 (concurrent users would contaminate each other)
- `contextvars.ContextVar` — adds async-specific complexity; wrong tool for I/O-bound request handling

---

## Decision 3 — AI System Prompt Localisation

**Decision**: Keep `SESSION_ANALYSIS_SYSTEM_PROMPT` as a constant. `analyse_session()` accepts `language: str = "en"` and appends a language instruction suffix at call time from a `_LANGUAGE_INSTRUCTIONS` dict.

**Rationale**: Duplicating the full 50-line JSON-schema prompt in Russian creates a maintenance hazard (any schema change requires parallel edits). Claude reliably follows a final language instruction appended to the system prompt. Adding a new language requires only one new dict entry, satisfying FR-009.

Russian instruction to append:
> "Respond entirely in Russian. All narrative text, section explanations, recommendations, and notes must be in Russian. Numeric values, units (mg/dL), and JSON keys must remain unchanged."

**Alternatives considered**:
- Full Russian system prompt — maintenance hazard (duplicate diverge)
- Runtime machine translation — corrupts MarkdownV2 escape sequences; adds latency and external dependency

---

## Decision 4 — DB Storage for Language Preference

**Decision**: Add `language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)` directly to the existing `User` model. Application default is `"en"` when `NULL`.

**Rationale**: Language preference is a simple scalar attribute of a user, not a separate entity. A separate `UserLanguagePreference` table would add a join on every message, a new repository, and unnecessary structural complexity. `nullable=True` with an application-level default satisfies FR-008 (default to English if absent) and avoids a NOT NULL migration on existing rows.

**Alternatives considered**:
- Separate `UserLanguagePreference` table — overengineering for a single scalar; one unnecessary join per message
- `String(2)` fixed-length — too short for future codes (e.g., `zh-CN`); `String(10)` allows BCP-47 tags

---

## Decision 5 — No New Library Dependency

**Decision**: No new pip dependency. The dict catalogue approach requires only stdlib Python.

**Rationale**: All translator libraries receive either pre-escaped or raw text and would need to know about MarkdownV2 escaping. Managing that boundary is more complex than maintaining a bilingual dict of pre-composed, already-escaped templates. The dict catalogue keeps escaping in one place (formatter functions) and keeps translated strings as literal, inspectable Python strings.

---

## Summary

| Concern | Approach |
|---|---|
| Translation catalogue | `bot/i18n.py` — nested dict + `t(key, lang, **kwargs)` |
| Formatter signatures | `lang: str = "en"` kwarg on all ~20 public formatters |
| AI language instruction | Append suffix to system prompt at call time |
| DB storage | `language_code` column on `User` model (`nullable=True`) |
| New library | None |
