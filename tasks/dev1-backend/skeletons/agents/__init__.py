"""GovCapture agent definitions for the Hermes runtime.

Each constant in this package describes one of the five agents that participate
in a capture run. The fields are consumed by /api/agent/hermes_runner.py to
build the `delegate_task` calls.

Wiring summary (read tasks/AGENT_ARCHITECTURE.md for the full design):

    Capture Lead (orchestrator, depth 0)
        ↓ delegate_task(role="orchestrator", toolsets=[gov_documents, gov_compliance, gov_risks, gov_proposals, human_review])
    Capture Analyst (orchestrator, depth 1) × N parallel
        ↓ delegate_task(role="leaf", toolsets=[gov_compliance])
    Compliance Officer (leaf, depth 2)
        ↓ returns {requirements, fit_score} — §11.1 enforced
    [if not reject]
        ↓ delegate_task(role="leaf", toolsets=[gov_risks])
    Risk Analyst (leaf, depth 2)
        ↓ delegate_task(role="leaf", toolsets=[gov_proposals])
    Proposal Strategist (leaf, depth 2)
"""

from .agent_def import AgentDef
from .capture_lead import CAPTURE_LEAD
from .capture_analyst import CAPTURE_ANALYST
from .compliance_officer import COMPLIANCE_OFFICER
from .risk_analyst import RISK_ANALYST
from .proposal_strategist import PROPOSAL_STRATEGIST


ALL_AGENTS: dict[str, AgentDef] = {
    a.role_id: a for a in (
        CAPTURE_LEAD,
        CAPTURE_ANALYST,
        COMPLIANCE_OFFICER,
        RISK_ANALYST,
        PROPOSAL_STRATEGIST,
    )
}


__all__ = [
    "AgentDef",
    "ALL_AGENTS",
    "CAPTURE_LEAD",
    "CAPTURE_ANALYST",
    "COMPLIANCE_OFFICER",
    "RISK_ANALYST",
    "PROPOSAL_STRATEGIST",
]
