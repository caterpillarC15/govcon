"""Proposal Strategist — specialist subagent (leaf, depth 2).

Produces the §10.3 action package. Two modes:
    - "full"           — pursue / strong_pursue / maybe (LLM-backed)
    - "reject_summary" — reject (deterministic; no LLM call)

The mode is set by the Capture Analyst's branching logic. The skill itself
(generate_action_package) routes between an LLM call and a deterministic
constructor.
"""
from pathlib import Path
from .agent_def import AgentDef


PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


PROPOSAL_STRATEGIST = AgentDef(
    role_id="proposal_strategist",
    role="leaf",
    toolsets=(
        "gov_proposals",     # generate_action_package
    ),
    instructions_path=PROMPTS_DIR / "agent_proposal_strategist.md",
    persona_excerpt=(
        "Senior proposal lead, 20+ yrs of winning (and stopping losing) "
        "federal proposals. Pragmatic. Pro-human-review. Document-grade output. "
        "Generic salutations only — never invents recipient names."
    ),
    skills_loaded_on_demand=(
        "generate_full_action_package",     # for non-reject decisions
        "generate_reject_summary",           # deterministic; for reject only
    ),
    # Sonnet for full mode synthesis; reject mode bypasses LLM entirely.
    default_model="claude-sonnet-4-6",
)
