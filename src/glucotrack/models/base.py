"""SQLAlchemy declarative base and shared helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    pass


def new_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())
