"""extract_requirements — convert parsed PDF chunks into structured §10.1 requirements.

LLM-backed (Anthropic). Output is constrained server-side via `output_config.format`
(no parse-and-retry loop). After the call we apply post-validation:

    1. Page-number bounds: out-of-range page_numbers are nulled and confidence
       is downgraded to "low".
    2. Evidence binding: medium/high confidence requirements without an
       evidence_snippet are downgraded to "low".
    3. Fuzzy-match check: medium/high evidence_snippets that don't appear in
       the parsed source text (similarity < 0.3) are downgraded to "low".

Per CONTRACTS.md §5, the skill returns its data plus latency/cost metrics.
The trace bridge (A9) wraps this into a `tool_returned` event.
"""
from __future__ import annotations

import json
import logging
from difflib import SequenceMatcher
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from api.config import settings
from api.llm import LLM, LLMError, LLMMetrics
from api.skills.parse_pdf import ParsedChunk, ParsePdfOutput

logger = logging.getLogger(__name__)

PROMPT_PATH = __import__("pathlib").Path(__file__).parent / "prompt.txt"
RAW_PROMPT = PROMPT_PATH.read_text()
_SYSTEM_TAG = "### SYSTEM ###"
_USER_TAG = "### USER ###"
SYSTEM_PROMPT = RAW_PROMPT.split(_SYSTEM_TAG, 1)[1].split(_USER_TAG, 1)[0].strip()
USER_TEMPLATE = RAW_PROMPT.split(_USER_TAG, 1)[1].strip()

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
    """The skill output's per-requirement shape — matches PRD §10.1.

    Server-set fields (id, opportunity_id, created_at) live on the persisted
    `ExtractedRequirement` entity (api.schemas.extracted_requirement) and are
    added by the repository layer when the skill output gets persisted.
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


def _printable_ratio_okay(text: str) -> bool:
    if not text:
        return False
    return sum(c.isprintable() for c in text) / max(1, len(text)) >= 0.8


def _fuzzy_in_pages(snippet: str, chunks: list[ParsedChunk], page_number: int | None) -> bool:
    """Return True if the snippet appears (loosely) in the source — start with the
    requirement's reported page, then fall back to scanning all pages.

    The fuzzy threshold is intentionally lenient because pypdf often inserts/drops
    whitespace and reorders columns; we only flag clear hallucinations.
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
    output: RequirementExtractionOutput, parsed: ParsePdfOutput
) -> RequirementExtractionOutput:
    """Apply PRD §11 evidence-binding rules after the LLM returns.

    Downgrades happen in place — a 'high' confidence requirement with a
    fabricated page_number or unverifiable snippet drops to 'low'.
    """
    page_numbers_seen = {c.page_number for c in parsed.chunks}
    cleaned: list[ExtractedRequirementLLM] = []

    for req in output.requirements:
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

    return output.model_copy(update={"requirements": cleaned})


async def extract_requirements(
    payload: ExtractInput | dict[str, Any],
    *,
    llm: LLM | None = None,
    model: str | None = None,
) -> tuple[RequirementExtractionOutput, LLMMetrics]:
    """Extract structured requirements from a parsed PDF.

    Returns the validated §10.1 output plus the LLM metrics block (latency_ms,
    cost_usd, token counts, attempts). Caller is responsible for emitting the
    `tool_returned` trace event.

    On unparseable input, returns an empty result with a synthetic `latency_ms=0`
    metrics block — no LLM call is made.
    """
    if isinstance(payload, dict):
        payload = ExtractInput.model_validate(payload)

    parsed = payload.parsed
    doc_id = payload.doc_id or parsed.doc_id

    if parsed.unparseable or not parsed.chunks:
        logger.info("extract_requirements: skipping unparseable doc %s", doc_id)
        empty = RequirementExtractionOutput(
            requirements=[],
            missing_fields=["all"],
            conflicts=[],
        )
        metrics = LLMMetrics(
            model=model or settings.llm_dev_model,
            latency_ms=0,
            cost_usd=0.0,
            attempts=0,
        )
        return empty, metrics

    chunks_text = "\n\n".join(
        f"[page {c.page_number}]\n{c.text}" for c in parsed.chunks
    )
    user_prompt = USER_TEMPLATE.format(
        opportunity_metadata=json.dumps(payload.opportunity_metadata, indent=2, sort_keys=True),
        chunks=chunks_text,
        doc_id=doc_id,
    )

    llm = llm or LLM()
    try:
        raw, metrics = await llm.complete_structured(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            output_model=RequirementExtractionOutput,
            model=model,
        )
    except LLMError as exc:
        logger.error("extract_requirements: LLM failed for %s: %s", doc_id, exc)
        # Degraded-but-valid output so the planner can recover (PRD §4.5).
        return (
            RequirementExtractionOutput(
                requirements=[],
                missing_fields=["all"],
                conflicts=[],
            ),
            LLMMetrics(
                model=model or settings.llm_dev_model,
                latency_ms=0,
                cost_usd=0.0,
                attempts=1,
            ),
        )

    return _post_validate(raw, parsed), metrics
