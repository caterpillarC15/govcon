from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Annotated

import httpx
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from supabase import AsyncClient

from api.config import settings
from api.db import get_client
from api.rate_limit import RateLimitError, acquire
from api.repositories.api_key import ApiKeyRepository


class AuthenticatedUser(BaseModel):
    id: uuid.UUID
    email: str | None = None


class InternalActor(BaseModel):
    name: str = "internal"


class AgentActor(BaseModel):
    """An authenticated agent. Either an internal call or a per-user gck_ key."""

    is_internal: bool
    owner_profile_id: uuid.UUID | None = None
    api_key_id: uuid.UUID | None = None


async def require_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthenticatedUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth is not configured",
        )

    api_key = settings.supabase_anon_key or settings.supabase_service_role_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase API key is not configured",
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": api_key,
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth verification failed",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )

    body = response.json()
    user_id = body.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )

    try:
        parsed_id = uuid.UUID(str(user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        ) from exc

    return AuthenticatedUser(id=parsed_id, email=body.get("email"))


async def require_internal_actor(
    x_internal_api_key: Annotated[str | None, Header(alias="X-Internal-API-Key")] = None,
) -> InternalActor:
    configured = settings.internal_api_key
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API key is not configured",
        )
    if not x_internal_api_key or not secrets.compare_digest(
        x_internal_api_key,
        configured,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )
    return InternalActor()


async def require_agent_or_internal(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_internal_api_key: Annotated[
        str | None, Header(alias="X-Internal-API-Key")
    ] = None,
    client: AsyncClient = Depends(get_client),
) -> AgentActor:
    """Auth for /api/v1/tools/<name>: accept either INTERNAL_API_KEY or gck_."""
    # Path A: internal shared secret (Sprint B compatibility).
    configured = settings.internal_api_key
    if (
        x_internal_api_key
        and configured
        and secrets.compare_digest(x_internal_api_key, configured)
    ):
        return AgentActor(is_internal=True)

    # Path B: per-user gck_ bearer.
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Missing credentials"
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token.startswith("gck_"):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Token must be a gck_ API key (mint at /app/keys)",
        )
    digest = hashlib.sha256(token.encode()).hexdigest()
    repo = ApiKeyRepository(client)
    row = await repo.find_active_by_hash(digest)
    if row is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or revoked API key"
        )

    api_key_id = uuid.UUID(str(row["id"]))
    # Per-key rate limit: 60 req/min, refill 1/s.
    try:
        await acquire(
            f"rl:apikey:{api_key_id}", capacity=60, refill_per_sec=1.0
        )
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc

    return AgentActor(
        is_internal=False,
        owner_profile_id=uuid.UUID(str(row["owner_profile_id"])),
        api_key_id=api_key_id,
    )
