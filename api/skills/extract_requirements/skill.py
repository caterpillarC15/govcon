"""extract_requirements — chunks emitter + validator (PRD v1.2.6).

Per the operating rule (devdocs/MICHAELA_SYSTEM_MODEL.md line 175),
the §10.1 ExtractedRequirement structuring is judgment work — Gate
performs it in her agent context (in /root/michealaai). This skill
holds the deterministic mechanics:

1. Returning parsed PDF chunks with page metadata for Gate to consume.
2. Enforcing PRD §11 evidence-binding rules on Gate-emitted
   requirements: page-bound checks, snippet presence, fuzzy-match
   against source text. Out-of-range pages are nulled; high/medium
   confidence without a verifiable snippet is downgraded to "low".

Two flows:
- requirements=None  → returns chunks only (Gate's first call).
- requirements=[…]   → validates + returns downgraded set.
"""
from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from api.skills.parse_pdf import ParsedChunk, ParsePdfOutput

logger = logging.getLogger(__name__)

FUZZY_MATCH_MIN = 0.3
"""Below this snippet/source similarity, downgrade evidence-bearing
requirements (PRD §11 evidence-binding rule)."""

REQ_TYPES = (
    "eligibility",
    "technical",
    "past_performance",
    "certification",
    "insurance",
    "bonding",
    "security",
    "submission",
    "evaluation",
    "deadline",
    "location",
    "pricing",
    "document_required",
)
ConfidenceLevel = Literal["high", "medium", "low", "unknown"]


class ExtractedRequirementLLM(BaseModel):
    """Per-requirement shape — matches PRD §10.1.

    Server-set fields (id, opportunity_id, created_at) live on the
    persisted entity (api.schemas.extracted_requirement) and are added
    by the repository layer. The "LLM" suffix on the class name is
    historical (kept for back-compat); these are now agent-emitted,
    not LLM-emitted-by-this-skill.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal[REQ_TYPES]  # type: ignore[valid-type]
    title: str = Field(..., min_length=1)
    value: str = ""
    description: str = ""
    confidence: ConfidenceLevel
    evidence_snippet: str = ""
    source_document: str = ""
    page_number: int | None = None
    is_blocker: bool = False


class RequirementConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    candidates: list[str] = Field(default_factory=list)
    requires_human_review: bool = True


class RequirementExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirements: list[ExtractedRequirementLLM] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    conflicts: list[RequirementConflict] = Field(default_factory=list)


class ExtractInput(BaseModel):
    parsed: ParsePdfOutput
    opportunity_metadata: dict[str, Any] = Field(default_factory=dict)
    doc_id: str | None = None
    # Agent-emitted requirements to validate. None = first call (Gate
    # gets chunks back, runs LLM in her context, calls again with
    # requirements populated).
    requirements: list[ExtractedRequirementLLM] | None = None
    missing_fields: list[str] = Field(default_factory=list)
    conflicts: list[RequirementConflict] = Field(default_factory=list)


def _fuzzy_in_pages(
    snippet: str, chunks: list[ParsedChunk], page_number: int | None
) -> bool:
    """Return True if the snippet appears (loosely) in the source.

    Start with the requirement's reported page, then fall back to
    scanning all pages. The fuzzy threshold is intentionally lenient
    because pypdf often inserts/drops whitespace and reorders
    columns; we only flag clear hallucinations.
    """
    if not snippet:
        return False
    target = snippet.strip()[:200]
    if not target:
        return False

    page_text_map = {c.page_number: c.text for c in chunks}
    candidates: list[str] = []
    if page_number in page_text_map:
        candidates.append(page_text_map[page_number])
    candidates.extend(c.text for c in chunks if c.page_number != page_number)

    for text in candidates:
        if not text:
            continue
        if target.casefold() in text.casefold():
            return True
        ratio = SequenceMatcher(None, target, text[:5000]).ratio()
        if ratio >= FUZZY_MATCH_MIN:
            return True
    return False


def _post_validate(
    requirements: list[ExtractedRequirementLLM], parsed: ParsePdfOutput
) -> list[ExtractedRequirementLLM]:
    """Apply PRD §11 evidence-binding rules.

    Downgrades happen in place — a 'high' confidence requirement with
    a fabricated page_number or unverifiable snippet drops to 'low'.
    """
    page_numbers_seen = {c.page_number for c in parsed.chunks}
    cleaned: list[ExtractedRequirementLLM] = []

    for req in requirements:
        update: dict[str, Any] = {}

        if req.page_number is not None and req.page_number not in page_numbers_seen:
            update["page_number"] = None
            if req.confidence in ("high", "medium"):
                update["confidence"] = "low"

        confidence = update.get("confidence", req.confidence)
        if confidence in ("high", "medium") and not req.evidence_snippet.strip():
            update["confidence"] = "low"

        confidence = update.get("confidence", req.confidence)
        if (
            confidence in ("high", "medium")
            and req.evidence_snippet.strip()
            and parsed.chunks
            and not _fuzzy_in_pages(
                req.evidence_snippet,
                parsed.chunks,
                update.get("page_number", req.page_number),
            )
        ):
            update["confidence"] = "low"

        cleaned.append(req.model_copy(update=update) if update else req)

    return cleaned


async def extract_requirements(
    payload: ExtractInput | dict[str, Any],
) -> dict[str, Any]:
    """Return chunks (and validated requirements, if supplied).

    Two-flow contract per PRD v1.2.6:
    - First call (requirements=None): caller (Gate's agent) needs the
      chunks to feed her LLM context. Returns chunks + empty
      requirements.
    - Second call (requirements=[…]): caller hands back the
      LLM-emitted requirements for §11 validation. Returns the
      downgraded set + chunks (for traceability).

    Unparseable PDFs return empty chunks + missing_fields=["all"].
    """
    if isinstance(payload, dict):
        payload = ExtractInput.model_validate(payload)

    parsed = payload.parsed
    doc_id = payload.doc_id or parsed.doc_id

    chunks_data = [
        {
            "page_number": c.page_number,
            "text": c.text,
            "doc_id": doc_id,
        }
        for c in parsed.chunks
    ]

    if parsed.unparseable or not parsed.chunks:
        logger.info("extract_requirements: skipping unparseable doc %s", doc_id)
        return {
            "chunks": chunks_data,
            "requirements": [],
            "missing_fields": ["all"],
            "conflicts": [],
        }

    requirements_in = payload.requirements or []
    validated = _post_validate(requirements_in, parsed)

    return {
        "chunks": chunks_data,
        "requirements": [r.model_dump() for r in validated],
        "missing_fields": payload.missing_fields,
        "conflicts": [c.model_dump() for c in payload.conflicts],
    }
