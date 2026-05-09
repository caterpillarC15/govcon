from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExtractedRequirementCreate(BaseModel):
    """Input shape for POST /opportunities/{id}/requirements.

    Server-set fields (id, opportunity_id, created_at) are omitted.
    opportunity_id comes from the URL path parameter.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "eligibility",
        "technical",
        "past_performance",
        "certification",
        "insurance",
        "bonding",
        "security",
        "submission",
        "evaluation",
        "deadline",
        "location",
        "pricing",
        "document_required",
    ]
    title: str = Field(..., min_length=1)
    value: str | None = None
    description: str | None = None
    confidence: Literal["high", "medium", "low", "unknown"]
    evidence_snippet: str | None = None
    source_document: str | None = None
    page_number: int | None = Field(None, ge=1)
    is_blocker: bool = False
