"""Repo for the api_keys table.

Mint returns (plaintext, row) — caller surfaces plaintext to user once.
Lookup is by sha256(plaintext) hash; the table has a unique index on it.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from supabase import AsyncClient

KEY_PREFIX = "gck"
KEY_RANDOM_BYTES = 32  # 256 bits of entropy in the plaintext.


def _generate_plaintext_key() -> tuple[str, str, str]:
    """Return (plaintext, prefix, sha256_hash). Plaintext: gck_<urlsafe>."""
    raw = secrets.token_urlsafe(KEY_RANDOM_BYTES)
    plaintext = f"{KEY_PREFIX}_{raw}"
    prefix = plaintext[:12]
    digest = hashlib.sha256(plaintext.encode()).hexdigest()
    return plaintext, prefix, digest


def hash_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


class ApiKeyRepository:
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def list_for_owner(self, owner_id: uuid.UUID) -> list[dict[str, Any]]:
        resp = await (
            self._client.table("api_keys")
            .select("*")
            .eq("owner_profile_id", str(owner_id))
            .order("created_at", desc=True)
            .execute()
        )
        return cast("list[dict[str, Any]]", resp.data or [])

    async def mint(
        self, owner_id: uuid.UUID, name: str
    ) -> tuple[str, dict[str, Any]]:
        plaintext, prefix, digest = _generate_plaintext_key()
        resp = await (
            self._client.table("api_keys")
            .insert(
                {
                    "owner_profile_id": str(owner_id),
                    "name": name,
                    "key_hash": digest,
                    "prefix": prefix,
                    "scopes": ["tools:*"],
                }
            )
            .execute()
        )
        rows = cast("list[dict[str, Any]]", resp.data or [])
        if not rows:
            raise RuntimeError("api_keys insert returned no row")
        return plaintext, rows[0]

    async def revoke(
        self, owner_id: uuid.UUID, key_id: uuid.UUID
    ) -> dict[str, Any] | None:
        resp = await (
            self._client.table("api_keys")
            .update({"revoked_at": datetime.now(timezone.utc).isoformat()})
            .eq("owner_profile_id", str(owner_id))
            .eq("id", str(key_id))
            .execute()
        )
        rows = cast("list[dict[str, Any]]", resp.data or [])
        return rows[0] if rows else None

    async def find_active_by_hash(self, key_hash: str) -> dict[str, Any] | None:
        resp = await (
            self._client.table("api_keys")
            .select("*")
            .eq("key_hash", key_hash)
            .is_("revoked_at", "null")
            .maybe_single()
            .execute()
        )
        if resp is None:
            return None
        return cast("dict[str, Any] | None", resp.data)
