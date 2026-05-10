from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    email: str | None = Field(None, max_length=320)
    full_name: str | None = Field(None, max_length=255)
    company_name: str | None = Field(None, max_length=255)
    role: Literal["owner", "consultant", "admin"] = "owner"
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(None, max_length=255)
    company_name: str | None = Field(None, max_length=255)
