"""Risk Analyst — specialist subagent (leaf, depth 2).

Skipped for reject decisions. Identifies risks across the 12 PRD §5.8
categories with calibrated severity. Cross-checks Compliance Officer
blockers; caps output at 8 actionable risks.
"""
from pathlib import Path
from .agent_def import AgentDef


PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


RISK_ANALYST = AgentDef(
    role_id="risk_analyst",
    role="leaf",
    toolsets=(
        "gov_risks",         # detect_risks
    ),
    instructions_path=PROMPTS_DIR / "agent_risk_analyst.md",
    persona_excerpt=(
        "Former internal auditor turned capture risk specialist. "
        "Skeptical but constructive. Calibrated severity sense. "
        "Names what to watch for; doesn't over-flag, doesn't under-flag."
    ),
    skills_loaded_on_demand=(
        "detect_risks_calibrated",
    ),
    # Risk detection is a structured-output classification task — Haiku is
    # sufficient and saves cost at scale.
    default_model="claude-haiku-4-5-20251001",
)
