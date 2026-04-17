"""Database initialisation and async session factory."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from glucotrack.models.base import Base

logger = logging.getLogger(__name__)

_engine = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> None:
    """Initialise the async SQLAlchemy engine. Call once at application startup."""
    global _engine, _async_session_factory
    _engine = create_async_engine(database_url, echo=False)
    _async_session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info("Database engine initialised: %s", database_url.split("///")[0])


async def init_db(database_url: str) -> None:
    """Create all tables. Safe to call multiple times (CREATE IF NOT EXISTS)."""
    init_engine(database_url)
    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession from the factory. Commits on success, rolls back on error."""
    if _async_session_factory is None:
        raise RuntimeError("Database engine not initialised. Call init_db() first.")
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_engine() -> None:
    """Dispose the engine connection pool. Call on application shutdown."""
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine closed.")


if __name__ == "__main__":
    """CLI: python -m glucotrack.db init"""
    import asyncio
    import sys
    import os

    if len(sys.argv) > 1 and sys.argv[1] == "init":
        db_url = os.environ.get(
            "DATABASE_URL", "sqlite+aiosqlite:///./data/glucotrack.db"
        )
        os.makedirs("data", exist_ok=True)
        asyncio.run(init_db(db_url))
        print(f"Database initialised: {db_url}")
    else:
        print("Usage: python -m glucotrack.db init")
        sys.exit(1)
