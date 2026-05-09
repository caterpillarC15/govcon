"""Capture Lead — root orchestrator agent.

Hermes spawns this as the root agent for every run. It owns the run-level
decisions: parse goal, find candidates, rank, delegate per-opportunity work
to Capture Analysts (in parallel), summarize.

Toolsets explicitly EXCLUDED:
    - gov_documents     (parse_pdf belongs to Capture Analysts)
    - gov_compliance    (extract_requirements + score_fit belong to Compliance Officer)
    - gov_risks         (detect_risks belongs to Risk Analyst)
    - gov_proposals     (generate_action_package belongs to Proposal Strategist)

This exclusion is the architectural enforcement: the Capture Lead must
delegate; it cannot do specialist work itself.
"""
from pathlib import Path
from .agent_def import AgentDef


# tasks/dev1-backend/skeletons/agents/capture_lead.py → ../../prompts/agent_capture_lead.md
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


CAPTURE_LEAD = AgentDef(
    role_id="capture_lead",
    role="orchestrator",
    toolsets=(
        "gov_discovery",     # parse_goal, search_sam, load_seeded, rank_opportunities, summarize_run
        "human_review",      # request_human_review (escalation)
    ),
    instructions_path=PROMPTS_DIR / "agent_capture_lead.md",
    persona_excerpt=(
        "Senior capture director, 20 yrs federal-contracting experience. "
        "Calm, summary-oriented. Orchestrates; specialists do the work. "
        "Cites specialist verdicts faithfully; never upgrades a reject."
    ),
    skills_loaded_on_demand=(
        "discover_opportunities",   # parse goal → search → fallback → rank
        # delegation pattern is inline in the agent's instructions, not a SKILL
    ),
    default_model=None,  # use config.yaml default (Sonnet for synthesis)
)
