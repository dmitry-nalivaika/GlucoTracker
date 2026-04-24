# Data Model: Russian Language Support (Feature 003)

**Branch**: `003-russian-language-support` | **Date**: 2026-04-24

---

## Modified Entities

### User (existing — modified)

Column `language_code` added to the `users` table.

```python
class User(Base):
    __tablename__ = "users"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), ...)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), ...)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # NULL → application treats as "en" (FR-008)
```

**Migration**: `ALTER TABLE users ADD COLUMN language_code VARCHAR(10) DEFAULT NULL`

**Constraints**:
- `nullable=True` — existing rows default to `NULL`; application resolves `NULL` → `"en"` (FR-008)
- Valid values: any code in `SupportedLanguage` enum (`"en"`, `"ru"`, extensible)
- Max 10 chars — accommodates BCP-47 tags (e.g., `"zh-CN"`)
- Scoped per user; no cross-user reads/writes (FR-010, Constitution II)

---

## New Value Types (no new tables)

### SupportedLanguage

A Python `StrEnum` (not a DB table — validation lives in the application layer, satisfying FR-009 extensibility):

```python
class SupportedLanguage(str, enum.Enum):
    EN = "en"
    RU = "ru"
```

Adding a new language requires: (1) a new enum member, (2) a new entry in `i18n.STRINGS`, (3) a new entry in `ai_service._LANGUAGE_INSTRUCTIONS`. No DB schema change, no structural change.

---

## New Modules (no new tables)

### `src/glucotrack/bot/i18n.py`

The translation catalogue. All user-facing bot strings in both languages. Structure:

```python
SUPPORTED: frozenset[str] = frozenset({"en", "ru"})
DEFAULT_LANG: str = "en"

STRINGS: dict[str, dict[str, str]] = {
    "welcome": {"en": "...", "ru": "..."},
    "photo_type_prompt": {"en": "...", "ru": "..."},
    # ... all ~20 message keys
}

def t(key: str, lang: str, **kwargs: object) -> str:
    """Translate key to lang, fall back to DEFAULT_LANG, apply format kwargs."""
    locale = lang if lang in SUPPORTED else DEFAULT_LANG
    template = STRINGS[key][locale]
    return template.format(**kwargs) if kwargs else template
```

---

## Entity Relationship Summary

```
User (existing)
  ├── telegram_user_id  PK
  ├── created_at
  ├── last_seen_at
  ├── language_code     ← NEW (nullable, app-default "en")
  └── sessions[]        ← unchanged relationship
```

No new foreign keys, no new tables, no new joins.

---

## Alembic Migration Plan

Since this project uses `Base.metadata.create_all()` for schema management (no Alembic yet),
the `language_code` column is added to the model definition. On fresh DB creation it is
included automatically. For existing DBs, a manual migration script or `init_db()` call
with `checkfirst=True` handles the column addition.
