from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.fit_score import Breakdown


class FitScoreCreate(BaseModel):
    """Input shape for POST /opportunities/{id}/fit-score.

    Server-set fields (id, opportunity_id, created_at) are omitted.
    opportunity_id comes from the URL path parameter.
    """

    model_config = ConfigDict(extra="forbid")

    company_profile_id: uuid.UUID
    total_score: int = Field(..., ge=0, le=100)
    decision: Literal["strong_pursue", "pursue", "maybe", "reject"]
    confidence: Literal["high", "medium", "low"]
    breakdown: Breakdown = Field(
        ...,
        description="Sub-scores per PRD §5.7 dimensions; sum should equal total_score.",
    )
    strengths: list[str]
    weaknesses: list[str]
    blockers: list[str]
    missing_info: list[str]
    recommended_next_action: str | None = None
