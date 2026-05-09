from fastapi import APIRouter
from sqlalchemy import text

from api.db import engine
from api.redis import redis_client

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    async with engine.connect() as conn:
        await conn.execute(text("select 1"))
    await redis_client.ping()
    return {"status": "ok"}
