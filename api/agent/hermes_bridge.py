"""Trace bridge for the Michaela seeded capture path.

This is the tracked HTTP bridge the API can run today. It does not pretend to
execute live SAM discovery or LLM-backed Hermes synthesis. It emits the same SSE
event contract that the full Hermes runner must emit, while using seeded
fixtures and deterministic persistence so demos have real data writes.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import redis.asyncio as aioredis
from supabase import AsyncClient

from api.repositories.action_package import ActionPackageRepository
from api.repositories.agent_run import AgentRunRepository
from api.repositories.company_profile import CompanyProfileRepository
from api.repositories.opportunity import OpportunityRepository
from api.skills.load_seeded_opportunities import load_seeded_opportunities
from api.skills.rank_opportunities import rank_opportunities

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

_SCORE_BY_BAND = {
    "strong_pursue": 88,
    "pursue": 74,
    "maybe": 62,
    "reject": 0,
}

_BREAKDOWN_BY_BAND: dict[str, dict[str, int]] = {
    "strong_pursue": {
        "capability": 18,
        "eligibility": 14,
        "naics": 9,
        "past_performance": 13,
        "certification": 8,
        "insurance_bonding": 9,
        "deadline": 9,
        "complexity": 4,
        "geography": 4,
    },
    "pursue": {
        "capability": 16,
        "eligibility": 13,
        "naics": 8,
        "past_performance": 10,
        "certification": 7,
        "insurance_bonding": 7,
        "deadline": 8,
        "complexity": 3,
        "geography": 2,
    },
    "maybe": {
        "capability": 15,
        "eligibility": 12,
        "naics": 8,
        "past_performance": 5,
        "certification": 7,
        "insurance_bonding": 5,
        "deadline": 7,
        "complexity": 2,
        "geography": 1,
    },
    "reject": {
        "capability": 0,
        "eligibility": 0,
        "naics": 0,
        "past_performance": 0,
        "certification": 0,
        "insurance_bonding": 0,
        "deadline": 0,
        "complexity": 0,
        "geography": 0,
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _channel(run_id: uuid.UUID) -> str:
    return f"agent-run:{run_id}"


def _manifest_map() -> dict[str, dict[str, Any]]:
    manifests: dict[str, dict[str, Any]] = {}
    if not FIXTURES_DIR.exists():
        return manifests
    for manifest_path in sorted(FIXTURES_DIR.glob("*/manifest.json")):
        if manifest_path.parent.name.startswith("_"):
            continue
        manifest = json.loads(manifest_path.read_text())
        manifests[manifest["slug"]] = manifest
    return manifests


def _parse_goal_heuristic(goal: str, profile: dict[str, Any] | None) -> dict[str, Any]:
    profile = profile or {}
    words = [word.strip(".,;:!?").lower() for word in goal.split()]
    keywords = [word for word in words if len(word) > 3][:8]
    return {
        "keywords": keywords,
        "naics_hints": profile.get("naics_codes") or [],
        "due_window_days": 90 if "90" in words else 30,
        "set_aside_pref": "small_business" if profile.get("small_business_status") else None,
        "geography": profile.get("location"),
        "agencies": [],
        "opportunity_type": "any",
    }


class TracePublisher:
    def __init__(
        self,
        *,
        redis: aioredis.Redis,
        run_repo: AgentRunRepository,
        run_id: uuid.UUID,
    ) -> None:
        self.redis = redis
        self.run_repo = run_repo
        self.run_id = run_id

    async def emit(self, event: dict[str, Any]) -> None:
        event.setdefault("ts", _utc_now())
        await self.run_repo.append_step(self.run_id, event)
        await self.redis.publish(_channel(self.run_id), json.dumps(event, default=str))

    async def step_started(self, step_id: uuid.UUID, label: str) -> None:
        await self.emit(
            {
                "type": "step_started",
                "run_id": str(self.run_id),
                "step_id": str(step_id),
                "label": label,
            }
        )

    async def step_completed(self, step_id: uuid.UUID, status: str = "complete") -> None:
        await self.emit(
            {
                "type": "step_completed",
                "run_id": str(self.run_id),
                "step_id": str(step_id),
                "status": status,
            }
        )

    async def tool_call(
        self,
        *,
        step_id: uuid.UUID,
        tool: str,
        input_data: dict[str, Any],
        rationale: str,
    ) -> float:
        await self.emit(
            {
                "type": "tool_called",
                "run_id": str(self.run_id),
                "step_id": str(step_id),
                "tool": tool,
                "input": input_data,
                "rationale": rationale,
            }
        )
        return perf_counter()

    async def tool_return(
        self,
        *,
        step_id: uuid.UUID,
        tool: str,
        started_at: float,
        output: dict[str, Any] | None,
        error: str | None = None,
    ) -> None:
        await self.emit(
            {
                "type": "tool_returned",
                "run_id": str(self.run_id),
                "step_id": str(step_id),
                "tool": tool,
                "output": output,
                "error": error,
                "latency_ms": int((perf_counter() - started_at) * 1000),
                "cost_usd": 0,
            }
        )


async def run_seeded_michaela_capture(
    *,
    redis: aioredis.Redis,
    client: AsyncClient,
    run_id: uuid.UUID,
) -> None:
    """Run the deterministic seeded capture flow and emit SSE trace events."""
    run_repo = AgentRunRepository(client)
    profile_repo = CompanyProfileRepository(client)
    opp_repo = OpportunityRepository(client)
    package_repo = ActionPackageRepository(client)
    publisher = TracePublisher(redis=redis, run_repo=run_repo, run_id=run_id)

    run = await run_repo.get(run_id)
    if run is None:
        return

    await run_repo.mark_running(run_id)
    company_profile_id = run.get("company_profile_id")
    company_profile = None
    if company_profile_id:
        company_profile = await profile_repo.get(uuid.UUID(str(company_profile_id)))

    await publisher.emit(
        {
            "type": "run_started",
            "run_id": str(run_id),
            "goal": str(run["goal"]),
            "profile_id": str(run.get("profile_id")) if run.get("profile_id") else None,
        }
    )

    if company_profile is None:
        await publisher.emit(
            {
                "type": "needs_human",
                "run_id": str(run_id),
                "question": "Add a company profile before Michaela can score opportunities.",
                "context": {"missing": "company_profile"},
            }
        )
        await run_repo.mark_completed(run_id, status="partial")
        await publisher.emit(
            {
                "type": "run_completed",
                "run_id": str(run_id),
                "status": "partial",
                "summary": "Run paused because no company profile was attached.",
            }
        )
        return

    parse_step = uuid.uuid4()
    await publisher.step_started(parse_step, "Michaela parses the capture goal")
    parse_input = {"goal": run["goal"], "company_profile": company_profile}
    started = await publisher.tool_call(
        step_id=parse_step,
        tool="parse_goal",
        input_data=parse_input,
        rationale="Michaela turns the user's goal into search criteria before delegation.",
    )
    parsed_goal = _parse_goal_heuristic(str(run["goal"]), company_profile)
    await publisher.tool_return(
        step_id=parse_step,
        tool="parse_goal",
        started_at=started,
        output=parsed_goal,
    )
    await publisher.step_completed(parse_step)

    discovery_step = uuid.uuid4()
    await publisher.step_started(discovery_step, "Scot loads seeded SAM opportunities")
    started = await publisher.tool_call(
        step_id=discovery_step,
        tool="load_seeded_opportunities",
        input_data={"slugs": None, "reason": "seeded demo-stable path"},
        rationale=(
            "Scot uses seeded fixtures because this tracked bridge does not claim "
            "live SAM execution."
        ),
    )
    loaded = await load_seeded_opportunities({"slugs": None}, client=client)
    await publisher.tool_return(
        step_id=discovery_step,
        tool="load_seeded_opportunities",
        started_at=started,
        output=loaded,
    )
    await publisher.step_completed(discovery_step)

    manifests = _manifest_map()
    scored: list[dict[str, Any]] = []
    for loaded_opp in loaded["opportunities"]:
        opp = await opp_repo.get(uuid.UUID(str(loaded_opp["id"])))
        if opp is None:
            continue
        manifest = manifests.get(str(loaded_opp["slug"]), {})
        band = manifest.get("expected_decision_band", "maybe")
        blockers = manifest.get("expected_critical_blockers") or []
        score = _SCORE_BY_BAND.get(band, 55)
        scored.append(
            {
                "opportunity_id": str(loaded_opp["id"]),
                "slug": loaded_opp["slug"],
                "decision": band,
                "total_score": score,
                "due_date": opp.get("due_date"),
            }
        )
        await _persist_seeded_fit_and_risks(
            opp_repo=opp_repo,
            opportunity_id=uuid.UUID(str(loaded_opp["id"])),
            company_profile_id=uuid.UUID(str(company_profile["id"])),
            decision=band,
            total_score=score,
            blockers=blockers,
        )

    rank_step = uuid.uuid4()
    await publisher.step_started(rank_step, "Lenny ranks opportunities with Gabby blockers applied")
    started = await publisher.tool_call(
        step_id=rank_step,
        tool="rank_opportunities",
        input_data={"scored": scored},
        rationale="Lenny orders candidates by decision band, score, and deadline.",
    )
    ranked = rank_opportunities({"scored": scored})
    await publisher.tool_return(
        step_id=rank_step,
        tool="rank_opportunities",
        started_at=started,
        output=ranked,
    )
    for item in ranked["ranked"]:
        await publisher.emit(
            {
                "type": "opportunity_ranked",
                "run_id": str(run_id),
                "opportunity_id": item["opportunity_id"],
                "score": item["total_score"],
                "decision": item["decision"],
            }
        )
    await publisher.step_completed(rank_step)

    ranked_ids = [uuid.UUID(str(item["opportunity_id"])) for item in ranked["ranked"]]
    await run_repo.set_opportunities(run_id, ranked_ids)
    selected = next((item for item in ranked["ranked"] if item["decision"] != "reject"), None)
    if selected is None and ranked["ranked"]:
        selected = ranked["ranked"][0]

    action_package_id = None
    if selected is not None:
        package_step = uuid.uuid4()
        await publisher.step_started(package_step, "Roy prepares the seeded action package")
        started = await publisher.tool_call(
            step_id=package_step,
            tool="generate_action_package",
            input_data={"opportunity_id": selected["opportunity_id"], "mode": "seeded"},
            rationale="Roy creates a deterministic review package for the top seeded opportunity.",
        )
        opportunity = await opp_repo.get(uuid.UUID(str(selected["opportunity_id"])))
        package = await package_repo.create(
            _seeded_action_package_payload(
                opportunity=opportunity or {},
                company_profile_id=uuid.UUID(str(company_profile["id"])),
                decision=str(selected["decision"]),
                fit_score=int(selected["total_score"]),
            )
        )
        action_package_id = uuid.UUID(str(package["id"]))
        await run_repo.set_selected_opportunity(run_id, uuid.UUID(str(selected["opportunity_id"])))
        await publisher.tool_return(
            step_id=package_step,
            tool="generate_action_package",
            started_at=started,
            output={"action_package_id": str(action_package_id)},
        )
        await publisher.step_completed(package_step)

    await run_repo.mark_completed(run_id, status="complete", action_package_id=action_package_id)
    await publisher.emit(
        {
            "type": "run_completed",
            "run_id": str(run_id),
            "status": "complete",
            "summary": (
                "Michaela completed a seeded GovCapture run. Live Hermes/SAM "
                "execution remains a separate bridge mode."
            ),
        }
    )


async def _persist_seeded_fit_and_risks(
    *,
    opp_repo: OpportunityRepository,
    opportunity_id: uuid.UUID,
    company_profile_id: uuid.UUID,
    decision: str,
    total_score: int,
    blockers: list[str],
) -> None:
    await opp_repo.create_fit_score(
        opportunity_id,
        {
            "company_profile_id": str(company_profile_id),
            "total_score": total_score,
            "decision": decision,
            "confidence": "high" if decision in {"strong_pursue", "reject"} else "medium",
            "breakdown": _BREAKDOWN_BY_BAND.get(decision, _BREAKDOWN_BY_BAND["maybe"]),
            "strengths": ["Seeded fixture aligns with the demo profile."]
            if decision != "reject"
            else [],
            "weaknesses": ["Seeded fixture requires review before live pursuit."]
            if decision == "maybe"
            else [],
            "blockers": blockers,
            "missing_info": [],
            "recommended_next_action": _recommended_action(decision),
        },
    )
    for blocker in blockers:
        await opp_repo.create_risk(
            opportunity_id,
            {
                "company_profile_id": str(company_profile_id),
                "category": "clearance_required_unavailable"
                if "clearance" in blocker.lower()
                else "set_aside_mismatch",
                "severity": "critical",
                "title": blocker,
                "description": blocker,
                "evidence": None,
                "mitigation": "Do not bid until the blocker is resolved.",
                "requires_human_review": True,
            },
        )


def _recommended_action(decision: str) -> str:
    if decision == "strong_pursue":
        return "Prepare the bid memo and begin proposal planning."
    if decision == "pursue":
        return "Review requirements and confirm resource availability."
    if decision == "maybe":
        return "Monitor and resolve the named gaps before committing."
    return "Do not pursue because a critical blocker is present."


def _seeded_action_package_payload(
    *,
    opportunity: dict[str, Any],
    company_profile_id: uuid.UUID,
    decision: str,
    fit_score: int,
) -> dict[str, Any]:
    title = opportunity.get("title", "selected opportunity")
    return {
        "opportunity_id": str(opportunity["id"]),
        "company_profile_id": str(company_profile_id),
        "executive_summary": (
            f"Seeded run package for {title}. Decision: {decision.replace('_', ' ')}."
        ),
        "decision": decision,
        "fit_score": fit_score,
        "fit_rationale": (
            "Deterministic seeded fixture ranking. Use for demo validation only; "
            "live Hermes/SAM mode must re-score from source documents."
        ),
        "compliance_matrix": [
            {
                "requirement": "Review source solicitation before external action",
                "status": "unclear",
                "evidence": None,
                "next_action": "Gabby must verify source-cited requirements in live mode.",
                "owner": "Gabby",
            }
        ],
        "risk_register": [],
        "proposal_checklist": [
            "Confirm eligibility and certifications.",
            "Review source attachments.",
            "Assign proposal owner.",
        ],
        "timeline": [
            {
                "date": opportunity.get("due_date"),
                "task": "Confirm bid/no-bid decision",
                "owner": "Michaela",
            }
        ],
        "partner_suggestions": [],
        "outreach_draft": None,
        "approval_required": [
            "Human approval required before contacting any contracting officer.",
            "Human approval required before claiming certifications or compliance.",
            "Human approval required before submitting any proposal material.",
            "Human approval required before sending external email.",
        ],
    }
