"""SQLAlchemy declarative base and shared helpers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column, MappedColumn
from sqlalchemy.types import String


def utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def new_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())
