from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from api.config import settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict[str, Any]:
    """SQLAlchemy engine config that honors Supabase's SSL requirement transparently.

    Supabase Postgres requires SSL (rejects plaintext). Local Postgres on
    `localhost` doesn't have a cert and would fail with `ssl=require`. We detect
    by hostname and turn SSL on for everything that isn't a loopback address.
    """
    kwargs: dict[str, Any] = {"echo": False, "pool_pre_ping": True}
    host = (urlparse(url).hostname or "").lower()
    if host not in ("localhost", "127.0.0.1", "::1", ""):
        kwargs["connect_args"] = {"ssl": "require"}
    return kwargs


engine: AsyncEngine = create_async_engine(
    settings.database_url, **_engine_kwargs(settings.database_url)
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.connect() as conn:
        await conn.execute(text("select 1"))


async def close_db() -> None:
    await engine.dispose()


__all__ = ["Base", "engine", "SessionLocal", "init_db", "close_db"]
