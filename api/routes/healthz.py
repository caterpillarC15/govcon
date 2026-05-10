from fastapi import APIRouter, Depends
from supabase import AsyncClient

from api.deps import get_supabase
from api.redis import redis_client

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz(client: AsyncClient = Depends(get_supabase)) -> dict[str, str]:
    # Tiny PostgREST round-trip — fails loudly if creds/URL are wrong.
    await client.table("company_profiles").select("id").limit(1).execute()
    await redis_client.ping()  # type: ignore[misc]  # redis-py async overload union
    return {"status": "ok"}
