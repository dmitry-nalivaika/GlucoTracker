"""Shared pytest fixtures — T017."""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from glucotrack.models.base import Base, new_uuid
from glucotrack.models.session import Session, SessionStatus
from glucotrack.models.user import User


@pytest_asyncio.fixture
async def test_db() -> AsyncSession:
    """In-memory SQLite async session with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def sample_user(test_db: AsyncSession) -> User:
    """A persisted User with telegram_user_id=100."""
    user = User(telegram_user_id=100)
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_session(test_db: AsyncSession, sample_user: User) -> Session:
    """An open Session belonging to sample_user."""
    sess = Session(
        id=new_uuid(),
        user_id=sample_user.telegram_user_id,
        status=SessionStatus.OPEN,
    )
    test_db.add(sess)
    await test_db.commit()
    await test_db.refresh(sess)
    return sess
