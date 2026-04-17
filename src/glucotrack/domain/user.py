"""User domain — creation and lookup logic.

All operations require user_id (Constitution II).
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from glucotrack.models.base import utcnow
from glucotrack.models.user import User
from glucotrack.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


async def get_or_create_user(db: AsyncSession, telegram_user_id: int) -> User:
    """Return the existing User or create a new one on first contact.

    Updates last_seen_at on every call.

    Args:
        db: Active async database session.
        telegram_user_id: The Telegram user ID (immutable identity for MVP).

    Returns:
        The User ORM instance.
    """
    repo = UserRepository(db)
    user = await repo.get_by_telegram_id(telegram_user_id)
    if user is None:
        logger.info("Creating new user for telegram_user_id=%d", telegram_user_id)
        user = await repo.create(telegram_user_id=telegram_user_id)
    else:
        user = await repo.update_last_seen(telegram_user_id)
    return user
