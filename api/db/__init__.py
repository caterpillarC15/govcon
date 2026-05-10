"""Supabase async client factory.

Tables are managed by `supabase/migrations/*.sql`. The FastAPI service talks to
them through Supabase PostgREST with a server-only service-role key.
"""
from __future__ import annotations

from supabase import AsyncClient, acreate_client

from api.config import settings

_client: AsyncClient | None = None


async def get_client() -> AsyncClient:
    """Return a process-wide singleton AsyncClient.

    SUPABASE_SERVICE_ROLE_KEY bypasses RLS — server-only. The browser must
    use the anon key (NEXT_PUBLIC_*).
    """
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        _client = await acreate_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client


async def close_client() -> None:
    """Best-effort shutdown hook — supabase-py manages the underlying httpx pool."""
    global _client
    _client = None


__all__ = ["AsyncClient", "get_client", "close_client"]
