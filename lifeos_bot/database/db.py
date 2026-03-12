from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from lifeos_bot.config import settings


engine: AsyncEngine | None = None
SessionMaker: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    global engine, SessionMaker
    if engine is not None:
        return

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    SessionMaker = async_sessionmaker(engine, expire_on_commit=False)


async def close_db() -> None:
    global engine
    if engine is None:
        return
    await engine.dispose()
    engine = None


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    if SessionMaker is None:
        raise RuntimeError("DB is not initialized")
    return SessionMaker
