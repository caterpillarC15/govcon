"""Validate that source JSON Schemas and the generated Pydantic models stay in sync.

Lightweight contract test: parses every fixture/example payload and asserts both the
source JSON Schema (via jsonschema) and the generated Pydantic model accept it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from api.schemas.action_package import ActionPackage
from api.schemas.agent_run import AgentRun
from api.schemas.agent_run_create import AgentRunCreate
from api.schemas.company_profile import CompanyProfile
from api.schemas.company_profile_create import CompanyProfileCreate
from api.schemas.extracted_requirement import ExtractedRequirement
from api.schemas.fit_score import FitScore
from api.schemas.opportunity import Opportunity
from api.schemas.risk_flag import RiskFlag
from api.schemas.trace_event import TraceEvent

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "schemas"


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text())


def test_every_source_schema_is_valid_json_schema() -> None:
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)


def test_pydantic_models_present_for_each_schema() -> None:
    """Make sure codegen emitted a model for every source schema."""
    expected = {p.stem.replace(".schema", "").replace("-", "_") for p in SCHEMAS.glob("*.schema.json")}
    generated = {p.stem for p in (REPO / "api" / "schemas").glob("*.py") if p.stem != "__init__"}
    missing = expected - generated
    assert not missing, f"missing generated models: {missing}. Run `make schemas`."


def test_company_profile_round_trip() -> None:
    schema = _load_schema("company-profile.schema.json")
    payload = {
        "id": "00000000-0000-4000-8000-000000000010",
        "name": "Acme Cyber LLC",
        "website": "https://acme.example",
        "description": "Cybersecurity for federal civilian agencies.",
        "capabilities": ["RMF", "incident response", "SIEM"],
        "industry_keywords": ["cybersecurity", "soc"],
        "naics_codes": ["541512", "541519"],
        "certifications": ["CMMC L2"],
        "small_business_status": True,
        "past_performance": [{"title": "FedRAMP audit assist", "agency": "GSA", "year": 2025}],
        "service_area": ["TX", "VA"],
        "preferred_role": "either",
        "created_at": "2026-05-09T14:00:00Z",
        "updated_at": "2026-05-09T14:00:00Z",
    }
    Draft202012Validator(schema).validate(payload)
    parsed = CompanyProfile.model_validate(payload)
    assert parsed.name == "Acme Cyber LLC"


def test_company_profile_create_minimal() -> None:
    schema = _load_schema("company-profile-create.schema.json")
    payload = {"name": "Acme"}
    Draft202012Validator(schema).validate(payload)
    parsed = CompanyProfileCreate.model_validate(payload)
    assert parsed.name == "Acme"


def test_opportunity_round_trip() -> None:
    schema = _load_schema("opportunity.schema.json")
    payload = {
        "id": "00000000-0000-4000-8000-000000000200",
        "slug": "opp-navy-cyber-001",
        "source_notice_id": "4a9d3090f78a463d8d38de29f6d5a6db",
        "title": "Cyber Operations Support",
        "agency": "Department of the Navy",
        "solicitation_number": "N0017826RFP0001",
        "notice_type": "Solicitation",
        "posted_date": "2026-04-01",
        "office_name": "NAVSEA",
        "psc_code": "R410",
        "resource_links": ["https://sam.gov/api/example/resource"],
        "opportunity_status": "open",
        "record_kind": "rfp",
        "source_url": "https://sam.gov/opp/abc",
        "due_date": "2026-07-01",
        "naics": "541512",
        "set_aside": "Total Small Business",
        "place_of_performance": "Norfolk, VA",
        "description": "Tier 2 SOC analysts.",
        "attachments": [{"filename": "RFP.pdf", "url": "https://sam.gov/x.pdf"}],
        "raw_payload": {"opp_id": "abc"},
        "created_at": "2026-05-09T14:00:00Z",
        "updated_at": "2026-05-09T14:00:00Z",
    }
    Draft202012Validator(schema).validate(payload)
    Opportunity.model_validate(payload)


def test_extracted_requirement_round_trip() -> None:
    payload = {
        "id": "00000000-0000-4000-8000-000000000400",
        "opportunity_id": "00000000-0000-4000-8000-000000000200",
        "type": "security",
        "title": "Secret clearance required",
        "value": "Secret",
        "confidence": "high",
        "evidence_snippet": "Personnel must hold a Secret clearance...",
        "source_document": "RFP.pdf",
        "page_number": 14,
        "is_blocker": True,
        "created_at": "2026-05-09T14:00:00Z",
    }
    ExtractedRequirement.model_validate(payload)


def test_fit_score_round_trip() -> None:
    payload = {
        "id": "00000000-0000-4000-8000-000000000500",
        "opportunity_id": "00000000-0000-4000-8000-000000000200",
        "company_profile_id": "00000000-0000-4000-8000-000000000010",
        "total_score": 88,
        "decision": "strong_pursue",
        "confidence": "high",
        "breakdown": {
            "capability": 18, "eligibility": 14, "naics": 9,
            "past_performance": 13, "certification": 8, "insurance_bonding": 9,
            "deadline": 9, "complexity": 4, "geography": 4,
        },
        "strengths": ["NAICS aligned"],
        "weaknesses": [],
        "blockers": [],
        "missing_info": [],
        "recommended_next_action": "Pursue with full proposal team.",
        "created_at": "2026-05-09T14:00:00Z",
    }
    fs = FitScore.model_validate(payload)
    assert fs.decision == "strong_pursue"


def test_risk_flag_round_trip() -> None:
    payload = {
        "id": "00000000-0000-4000-8000-000000000600",
        "opportunity_id": "00000000-0000-4000-8000-000000000200",
        "company_profile_id": "00000000-0000-4000-8000-000000000010",
        "category": "set_aside_mismatch",
        "severity": "critical",
        "title": "8(a) only — company not certified",
        "description": "Solicitation restricted to 8(a); company not on the list.",
        "requires_human_review": False,
        "created_at": "2026-05-09T14:00:00Z",
    }
    RiskFlag.model_validate(payload)


def test_action_package_round_trip() -> None:
    payload = {
        "id": "00000000-0000-4000-8000-000000000300",
        "opportunity_id": "00000000-0000-4000-8000-000000000200",
        "company_profile_id": "00000000-0000-4000-8000-000000000010",
        "executive_summary": "Strong fit; proceed with full proposal.",
        "decision": "strong_pursue",
        "fit_score": 88,
        "fit_rationale": "All eligibility met; capability and NAICS align.",
        "compliance_matrix": [
            {"requirement": "FedRAMP Moderate", "status": "met", "evidence": "p.14"}
        ],
        "risk_register": [{"risk": "Tight deadline", "severity": "moderate"}],
        "proposal_checklist": ["Past-performance refs", "CMMC L2 letter"],
        "timeline": [{"date": "2026-06-15", "task": "Draft technical volume"}],
        "approval_required": ["Outreach to teaming partner"],
        "created_at": "2026-05-09T14:00:00Z",
    }
    ActionPackage.model_validate(payload)


def test_agent_run_round_trip() -> None:
    payload = {
        "id": "00000000-0000-4000-8000-000000000001",
        "goal": "cyber 60d",
        "company_profile_id": "00000000-0000-4000-8000-000000000010",
        "status": "complete",
        "steps": [],
        "opportunities": [],
        "created_at": "2026-05-09T14:00:00Z",
    }
    AgentRun.model_validate(payload)


def test_agent_run_create_inline_profile() -> None:
    AgentRunCreate.model_validate({"goal": "cyber 60d", "profile": {"name": "Acme"}})
    AgentRunCreate.model_validate({"goal": "cyber 60d", "profile_id": "00000000-0000-4000-8000-000000000010"})


@pytest.mark.parametrize("line", (REPO / "schemas" / "trace-event.example.jsonl").read_text().splitlines())
def test_every_example_trace_event_parses(line: str) -> None:
    if not line.strip():
        return
    payload = json.loads(line)
    TraceEvent.model_validate(payload)
