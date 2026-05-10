"""Request models for POST /tools/<name>.

These mirror each skill's input contract. Where the underlying skill takes
`dict[str, Any]`, the model adds typed validation at the HTTP boundary so
FastAPI generates a 422 on malformed input. The skill itself remains
untouched.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from api.skills.extract_requirements import ExtractInput
from api.skills.parse_pdf import ParsePdfInput


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParseGoalRequest(_Strict):
    goal: str = Field(..., min_length=1)
    company_profile: dict[str, Any] = Field(default_factory=dict)


class ParsePdfRequest(_Strict):
    path: str = Field(..., min_length=1)
    doc_id: str | None = None

    def to_skill_input(self) -> ParsePdfInput:
        return ParsePdfInput(path=self.path, doc_id=self.doc_id)


class ExtractRequirementsRequest(_Strict):
    parsed: dict[str, Any]
    opportunity_metadata: dict[str, Any] = Field(default_factory=dict)
    doc_id: str | None = None
    # PRD v1.2.6: optional agent-emitted requirements for §11 validation.
    # First call (omit) returns chunks for the agent to consume.
    # Second call (include) returns validated requirements.
    requirements: list[dict[str, Any]] | None = None
    missing_fields: list[str] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)

    def to_skill_input(self) -> ExtractInput:
        return ExtractInput.model_validate(self.model_dump())


class ScoreFitRequest(_Strict):
    company_profile: dict[str, Any]
    requirements: list[dict[str, Any]]
    # PRD v1.2.6: Lenny supplies these after computing in her agent context.
    # Omit on the first call (returns "needs_score" if no §11.1 blockers).
    total_score: int | None = None
    score_breakdown: dict[str, Any] | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommended_next_action: str = ""


class DetectRisksRequest(_Strict):
    company_profile: dict[str, Any] = Field(default_factory=dict)
    opportunity: dict[str, Any] = Field(default_factory=dict)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    # PRD v1.2.6: Gate emits risks in her agent context; skill validates.
    risks: list[dict[str, Any]] = Field(default_factory=list)


class GenerateActionPackageRequest(_Strict):
    mode: Literal["full", "reject_summary"] = "full"
    company_profile: dict[str, Any] = Field(default_factory=dict)
    opportunity: dict[str, Any] = Field(default_factory=dict)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    fit_score: dict[str, Any] = Field(default_factory=dict)
    risks: list[dict[str, Any]] = Field(default_factory=list)


class SearchSamRequest(_Strict):
    keywords: str = ""
    naics: str | None = None
    posted_from: str | None = None
    set_aside: str | None = None
    state: str | None = None
    limit: int = Field(20, ge=1, le=100)


class FetchAttachmentRequest(_Strict):
    run_id: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    filename: str | None = None


class RankOpportunitiesRequest(_Strict):
    scored: list[dict[str, Any]]


class LoadSeededOpportunitiesRequest(_Strict):
    slugs: list[str] | None = None


class QueryUsaspendingRequest(_Strict):
    naics: str | None = None
    agency: str | None = None
    limit: int = Field(25, ge=1, le=100)
    award_type_codes: list[str] | None = Field(
        default=None,
        description=(
            "USASpending award type codes. Default: A/B/C/D (federal "
            "contracts). Override to query grants (02/03/04/05) etc."
        ),
    )
