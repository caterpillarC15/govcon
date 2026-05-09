from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from api.config import settings


class Base(DeclarativeBase):
    pass


engine: AsyncEngine = create_async_engine(
    settings.database_url, echo=False, pool_pre_ping=True
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.connect() as conn:
        await conn.execute(text("select 1"))


async def close_db() -> None:
    await engine.dispose()


__all__ = ["Base", "engine", "SessionLocal", "init_db", "close_db"]
