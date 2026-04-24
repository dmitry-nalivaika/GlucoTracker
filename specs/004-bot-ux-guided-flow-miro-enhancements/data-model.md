# Data Model: 004 — Bot UX: Guided Flow, Action Keyboard, Status Messages & Miro Card Enhancements

## Schema Changes

### `users` table — add `chat_id`

```sql
ALTER TABLE users ADD COLUMN chat_id BIGINT NULL;
```

| Column      | Type    | Nullable | Notes |
|-------------|---------|----------|-------|
| chat_id     | BIGINT  | YES      | Telegram chat ID; populated on first interaction; used for broadcast |

**Alembic migration**: `alembic/versions/004_add_chat_id.py`
- `revision = "004"`, `down_revision = "003"`
- `upgrade()`: `op.add_column("users", Column("chat_id", BigInteger, nullable=True))`
- `downgrade()`: `op.drop_column("users", "chat_id")`

---

## No New Tables

No new ORM models are required for this feature. The AI response extensions
(`executive_summary`, `encouragement`) are stored as part of the existing
`ai_analyses.raw_response TEXT` column.

---

## Repository Changes

### `UserRepository` — new methods

```python
async def update_chat_id(self, user_id: int, chat_id: int) -> None:
    """Persist chat_id for the user if it differs from the stored value."""

async def get_all_with_chat_id(self) -> list[User]:
    """Return all users who have a non-null chat_id (for broadcast)."""
```

Both methods satisfy Constitution II:
- `update_chat_id` is scoped by `user_id`
- `get_all_with_chat_id` returns only records with `chat_id IS NOT NULL`; used
  exclusively for broadcast and never leaks one user's data to another
