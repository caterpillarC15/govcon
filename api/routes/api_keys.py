"""HTTP routes for per-user API key management.

POST mints (plaintext returned ONCE).
GET lists prefixes (no plaintext, no hash).
DELETE soft-revokes via revoked_at; the key remains in the table for
audit but stops authenticating.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from supabase import AsyncClient

from api.auth import AuthenticatedUser, require_user
from api.deps import get_supabase
from api.repositories.api_key import ApiKeyRepository
from api.schemas.api_key import ApiKey, ApiKeyCreate, ApiKeyMint

router = APIRouter(prefix="/api/keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKey])
async def list_keys(
    user: AuthenticatedUser = Depends(require_user),
    client: AsyncClient = Depends(get_supabase),
) -> list[ApiKey]:
    repo = ApiKeyRepository(client)
    rows = await repo.list_for_owner(user.id)
    return [ApiKey.model_validate(r) for r in rows]


@router.post("", response_model=ApiKeyMint, status_code=201)
async def mint_key(
    payload: ApiKeyCreate,
    user: AuthenticatedUser = Depends(require_user),
    client: AsyncClient = Depends(get_supabase),
) -> ApiKeyMint:
    repo = ApiKeyRepository(client)
    plaintext, row = await repo.mint(user.id, payload.name)
    return ApiKeyMint(
        id=row["id"],
        name=row["name"],
        prefix=row["prefix"],
        plaintext_key=plaintext,
        created_at=row["created_at"],
    )


@router.delete("/{key_id}", status_code=204)
async def revoke_key(
    key_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    client: AsyncClient = Depends(get_supabase),
) -> None:
    repo = ApiKeyRepository(client)
    revoked = await repo.revoke(user.id, key_id)
    if revoked is None:
        raise HTTPException(404, "Key not found or not yours")
    return None
