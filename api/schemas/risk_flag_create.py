from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskFlagCreate(BaseModel):
    """Input shape for POST /opportunities/{id}/risks.

    Server-set fields (id, opportunity_id, created_at) are omitted.
    opportunity_id comes from the URL path parameter.
    """

    model_config = ConfigDict(extra="forbid")

    company_profile_id: uuid.UUID
    category: Literal[
        "clearance_required_unavailable",
        "set_aside_mismatch",
        "certification_gap",
        "past_performance_weakness",
        "deadline_too_close",
        "missing_or_unclear_attachments",
        "submission_ambiguity",
        "insurance_or_bonding_gap",
        "scope_mismatch",
        "legal_compliance_review_required",
        "pricing_complexity",
        "required_document_not_found",
    ]
    severity: Literal["critical", "major", "moderate", "minor"]
    title: str = Field(..., min_length=1)
    description: str
    evidence: str | None = None
    mitigation: str | None = None
    requires_human_review: bool = False
