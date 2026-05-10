"""Capture Analyst — per-opportunity orchestrator (depth 1).

Spawned by the Capture Lead, one per top-ranked opportunity, in parallel.
Owns ONE opportunity end to end: fetch attachments, parse PDFs, delegate
to Compliance Officer (extraction + scoring), then conditionally to Risk
Analyst and Proposal Strategist based on the §11.1-aware verdict.

Role = orchestrator (depth 1) so it can spawn specialist leaves.
"""
from pathlib import Path
from .agent_def import AgentDef


PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


CAPTURE_ANALYST = AgentDef(
    role_id="capture_analyst",
    role="orchestrator",
    toolsets=(
        "gov_documents",     # fetch_attachment, parse_pdf, verify_source_page
        "human_review",      # escalate when all PDFs unparseable
        # NOTE: no gov_compliance / gov_risks / gov_proposals — those go to specialists.
    ),
    instructions_path=PROMPTS_DIR / "agent_capture_analyst.md",
    persona_excerpt=(
        "Mid-career capture analyst, methodical and detail-oriented. "
        "Process-forward; defers to specialists. 'Two attachments fetched. "
        "Compliance Officer is reviewing.' Calm under failure; reports plainly."
    ),
    skills_loaded_on_demand=(
        "analyze_opportunity_e2e",   # the per-opportunity workflow
    ),
    default_model=None,  # inherit from delegation config (Sonnet by default)
)
