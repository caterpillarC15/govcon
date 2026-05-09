"""Compliance Officer — specialist subagent (leaf, depth 2).

The single source of truth for eligibility decisions. Owns PRD §11.1
enforcement. No other agent can override its verdict.

Role = leaf (cannot spawn further subagents). Toolset restricted to
gov_compliance only — extract_requirements + score_fit (which has the
§11.1 deterministic short-circuit).
"""
from pathlib import Path
from .agent_def import AgentDef


PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


COMPLIANCE_OFFICER = AgentDef(
    role_id="compliance_officer",
    role="leaf",
    toolsets=(
        "gov_compliance",    # extract_requirements + score_fit (§11.1 enforced inside score_fit)
        # NO human_review — escalation goes through the parent (Capture Analyst)
    ),
    instructions_path=PROMPTS_DIR / "agent_compliance_officer.md",
    persona_excerpt=(
        "Former U.S. Government contracting officer, 15 yrs gov experience. "
        "Conservative; says no easily and confidently. Cites exact L.4.1-style "
        "section references. 'Eligibility is binary. The answer is no.' "
        "Gatekeeper for PRD §11.1."
    ),
    skills_loaded_on_demand=(
        "extract_requirements_with_evidence",
        "score_fit_with_eligibility_check",   # PRD §11.1 — the most important skill
    ),
    # Use Sonnet for synthesis-heavy extraction; the §11.1 deterministic check
    # is in Python and runs independent of model choice.
    default_model="claude-sonnet-4-6",
)
