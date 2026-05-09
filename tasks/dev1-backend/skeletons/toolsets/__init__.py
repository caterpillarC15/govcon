"""GovCapture toolsets — registered with Hermes for agent tool-calling.

Five domain toolsets plus Hermes built-ins (web, etc.). Each toolset is a
collection of Python functions with declared input/output schemas. Hermes'
agents call these by name; toolset restriction (per delegate_task) controls
which agent has access to which toolset.

Toolset → Agent mapping (from CONTRACTS.md §5):

    gov_discovery   → Capture Lead only
        parse_goal, search_sam_opportunities, load_seeded_opportunities,
        rank_opportunities, summarize_run

    gov_documents   → Capture Analyst only
        fetch_attachment, parse_pdf, verify_source_page

    gov_compliance  → Compliance Officer only
        extract_requirements, score_fit (with §11.1 enforcement)

    gov_risks       → Risk Analyst only
        detect_risks

    gov_proposals   → Proposal Strategist only
        generate_action_package

    human_review    → all agents (escalation gate)
        request_human_review

Implementation lives in /api/skills/<skill_name>/implementation.py per A4–A8.
This skeletons/ directory contains the function signatures and registration
metadata so devs know exactly what to fill in.
"""

# When integrating with Hermes, register each function via Hermes' tool/toolset
# API. The exact mechanism (decorator, manifest, plugin) is resolved during
# the A9 Hermes-integration spike. Until then, these stubs document the
# contract.

__all__ = [
    "GOV_DISCOVERY",
    "GOV_DOCUMENTS",
    "GOV_COMPLIANCE",
    "GOV_RISKS",
    "GOV_PROPOSALS",
    "HUMAN_REVIEW",
]


# Toolset manifests: name → (description, list of tool function names)
GOV_DISCOVERY = {
    "name": "gov_discovery",
    "description": "Federal opportunity discovery and ranking. Capture Lead toolset.",
    "tools": [
        "parse_goal",
        "search_sam_opportunities",
        "load_seeded_opportunities",
        "rank_opportunities",
        "summarize_run",
    ],
}

GOV_DOCUMENTS = {
    "name": "gov_documents",
    "description": "Solicitation document fetching and parsing. Capture Analyst toolset.",
    "tools": [
        "fetch_attachment",
        "parse_pdf",
        "verify_source_page",
    ],
}

GOV_COMPLIANCE = {
    "name": "gov_compliance",
    "description": "Requirement extraction and fit scoring with §11.1 enforcement. Compliance Officer toolset.",
    "tools": [
        "extract_requirements",
        "score_fit",
    ],
}

GOV_RISKS = {
    "name": "gov_risks",
    "description": "Risk detection across PRD §5.8 categories. Risk Analyst toolset.",
    "tools": [
        "detect_risks",
    ],
}

GOV_PROPOSALS = {
    "name": "gov_proposals",
    "description": "Action package generation per PRD §10.3. Proposal Strategist toolset.",
    "tools": [
        "generate_action_package",
    ],
}

HUMAN_REVIEW = {
    "name": "human_review",
    "description": "Human-in-the-loop escalation. Available to all agents.",
    "tools": [
        "request_human_review",
    ],
}
