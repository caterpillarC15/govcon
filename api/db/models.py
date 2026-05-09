"""SQLAlchemy 2.0 ORM models — PRD §8 tables.

Conventions:
- UUID PK with Python-side `default=uuid.uuid4` so unit tests don't need a DB connection.
- JSONB for list/dict fields (Postgres-only — single-DB project).
- `created_at` server default; `updated_at` server default + `onupdate=func.now()`.
- Foreign keys cascade for run-scoped data (requirements/scores/risks/packages tied to opportunities).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    capabilities: Mapped[list[str]] = mapped_column(JSONB, default=list)
    industry_keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_area: Mapped[list[str]] = mapped_column(JSONB, default=list)
    naics_codes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    certifications: Mapped[list[str]] = mapped_column(JSONB, default=list)
    small_business_status: Mapped[bool] = mapped_column(Boolean, default=False)
    sam_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    clearance_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    past_performance: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    insurance_bonding_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_contract_size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_role: Mapped[str] = mapped_column(String(32), default="either")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512))
    agency: Mapped[str] = mapped_column(String(255))
    solicitation_number: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    naics: Mapped[str | None] = mapped_column(String(32), nullable=True)
    set_aside: Mapped[str | None] = mapped_column(String(128), nullable=True)
    place_of_performance: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExtractedRequirement(Base):
    __tablename__ = "extracted_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
    )
    type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(512))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(16))
    evidence_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document: Mapped[str | None] = mapped_column(String(512), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_blocker: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FitScore(Base):
    __tablename__ = "fit_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
    )
    company_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_profiles.id", ondelete="CASCADE"),
    )
    total_score: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[str] = mapped_column(String(16))
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    strengths: Mapped[list[str]] = mapped_column(JSONB, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSONB, default=list)
    blockers: Mapped[list[str]] = mapped_column(JSONB, default=list)
    missing_info: Mapped[list[str]] = mapped_column(JSONB, default=list)
    recommended_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RiskFlag(Base):
    __tablename__ = "risk_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        index=True,
    )
    company_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_profiles.id", ondelete="CASCADE"),
    )
    category: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    mitigation: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ActionPackage(Base):
    __tablename__ = "action_packages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
    )
    company_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_profiles.id", ondelete="CASCADE"),
    )
    executive_summary: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(32))
    fit_score: Mapped[int] = mapped_column(Integer)
    fit_rationale: Mapped[str] = mapped_column(Text)
    compliance_matrix: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    risk_register: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    proposal_checklist: Mapped[list[str]] = mapped_column(JSONB, default=list)
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    partner_suggestions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    outreach_draft: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    approval_required: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal: Mapped[str] = mapped_column(Text)
    company_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("company_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), index=True, default="pending")
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    opportunities: Mapped[list[str]] = mapped_column(JSONB, default=list)
    selected_opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_package_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("action_packages.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


__all__ = [
    "CompanyProfile",
    "Opportunity",
    "ExtractedRequirement",
    "FitScore",
    "RiskFlag",
    "ActionPackage",
    "AgentRun",
]
