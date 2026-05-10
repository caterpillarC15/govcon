from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WaitlistSignupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=3, max_length=320)
    company: str | None = Field(None, max_length=255)
    role: str | None = Field(None, max_length=120)
    source: str | None = Field("landing", max_length=80)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        local, sep, domain = normalized.partition("@")
        if not sep or not local or "." not in domain or domain.startswith("."):
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("company", "role", "source")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class WaitlistSignupResponse(BaseModel):
    status: Literal["ok"] = "ok"
    already_registered: bool
