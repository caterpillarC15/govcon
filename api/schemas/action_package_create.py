from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.action_package import (
    ComplianceMatrixItem,
    OutreachDraft,
    PartnerSuggestion,
    RiskRegisterItem,
    TimelineItem,
)


class ActionPackageCreate(BaseModel):
    """Input shape for POST /action-packages.

    Server-set fields (id, created_at) are omitted.
    Both opportunity_id and company_profile_id are supplied in the body
    since this is a top-level resource (not nested under a parent URL).
    """

    model_config = ConfigDict(extra="forbid")

    opportunity_id: uuid.UUID
    company_profile_id: uuid.UUID
    executive_summary: str
    decision: str
    fit_score: int = Field(..., ge=0, le=100)
    fit_rationale: str
    compliance_matrix: list[ComplianceMatrixItem]
    risk_register: list[RiskRegisterItem]
    proposal_checklist: list[str]
    timeline: list[TimelineItem]
    partner_suggestions: list[PartnerSuggestion] | None = None
    outreach_draft: OutreachDraft | None = None
    approval_required: list[str] = Field(
        ...,
        description="Items requiring human gate before execution.",
    )
