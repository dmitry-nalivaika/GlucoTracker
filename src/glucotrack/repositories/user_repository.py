"""UserRepository — data access for User entities.

Every query must include user_id scope (Constitution II).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from glucotrack.models.base import utcnow
from glucotrack.models.user import User


def effective_lang(user: User | None) -> str:
    """Return the user's language code, defaulting to 'en' if unset (FR-008)."""
    if user is None or user.language_code is None:
        return "en"
    lang: str = user.language_code
    return lang


logger = logging.getLogger(__name__)


class UserRepository:
    """Async repository for User persistence."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        """Return the User with the given Telegram user ID, or None."""
        result = await self._db.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, telegram_user_id: int) -> User:
        """Create and persist a new User."""
        now = utcnow()
        user = User(
            telegram_user_id=telegram_user_id,
            created_at=now,
            last_seen_at=now,
        )
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        logger.debug("Created user telegram_user_id=%d", telegram_user_id)
        return user

    async def update_language(self, telegram_user_id: int, language_code: str) -> User:
        """Persist language preference for the given user (FR-002)."""
        user = await self.get_by_telegram_id(telegram_user_id)
        if user is None:
            raise ValueError(f"User {telegram_user_id} not found")
        user.language_code = language_code
        await self._db.flush()
        await self._db.refresh(user)
        logger.debug("Updated language for user %d to %s", telegram_user_id, language_code)
        return user

    async def update_last_seen(self, telegram_user_id: int) -> User:
        """Update last_seen_at for the given user and return the updated record."""
        user = await self.get_by_telegram_id(telegram_user_id)
        if user is None:
            raise ValueError(f"User {telegram_user_id} not found")
        user.last_seen_at = utcnow()
        await self._db.flush()
        await self._db.refresh(user)
        return user
