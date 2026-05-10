"""Pydantic models for the api_keys table.

ApiKey is the row shape (read paths).
ApiKeyMint includes plaintext_key — emitted ONCE when minting; never
retrievable thereafter.
ApiKeyCreate is the request payload for POST /api/keys.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiKey(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    owner_profile_id: UUID
    name: str
    prefix: str
    scopes: list[str]
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class ApiKeyMint(BaseModel):
    id: UUID
    name: str
    prefix: str
    plaintext_key: str = Field(..., description="Show ONCE. Never retrievable.")
    created_at: datetime


class ApiKeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=120)
