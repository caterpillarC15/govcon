"""extract_requirements — deterministic chunks emitter + validator (PRD v1.2.6).

The skill no longer calls an LLM. Gate emits §10.1 ExtractedRequirement
structures in her agent context; this skill holds the mechanics:

1. Returns parsed PDF chunks with page metadata.
2. Validates agent-supplied requirements against PRD §11 rules
   (page-bounds, evidence binding, fuzzy-match).
"""
from __future__ import annotations

from api.skills.extract_requirements.skill import (
    ExtractedRequirementLLM,
    ExtractInput,
    extract_requirements,
)
from api.skills.parse_pdf import ParsedChunk, ParsePdfOutput


def _make_parsed(chunks: list[tuple[int, str]]) -> ParsePdfOutput:
    return ParsePdfOutput(
        doc_id="RFP-test",
        page_count=max(p for p, _ in chunks) if chunks else 0,
        unparseable=False,
        chunks=[ParsedChunk(page_number=p, text=t, char_count=len(t)) for p, t in chunks],
    )


def _req(**overrides) -> ExtractedRequirementLLM:
    """Build a typical requirement with sensible defaults for tests."""
    base = {
        "type": "technical",
        "title": "Test requirement",
        "value": "x",
        "description": "y",
        "confidence": "high",
        "evidence_snippet": "",
        "source_document": "RFP-test",
        "page_number": 1,
        "is_blocker": False,
    }
    base.update(overrides)
    return ExtractedRequirementLLM(**base)


# ─── Chunks emitter (first-call flow) ──────────────────────────────────────


async def test_first_call_returns_chunks_with_page_metadata() -> None:
    """Without requirements supplied, the skill returns parsed chunks
    so Gate can feed them to her LLM context."""
    parsed = _make_parsed(
        [
            (1, "Personnel must hold a Secret clearance prior to award."),
            (2, "Bid bond required: 5% of total bid amount."),
        ]
    )
    out = await extract_requirements(ExtractInput(parsed=parsed))

    assert len(out["chunks"]) == 2
    assert out["chunks"][0]["page_number"] == 1
    assert "Secret clearance" in out["chunks"][0]["text"]
    assert out["chunks"][0]["doc_id"] == "RFP-test"
    assert out["requirements"] == []
    assert out["missing_fields"] == []


# ─── Validator (second-call flow) ──────────────────────────────────────────


async def test_validated_requirements_pass_through_unchanged() -> None:
    parsed = _make_parsed(
        [
            (1, "Personnel must hold a Secret clearance prior to award."),
            (2, "Bid bond required: 5% of total bid amount."),
        ]
    )
    requirements = [
        _req(
            type="security",
            title="Secret clearance",
            confidence="high",
            evidence_snippet="Personnel must hold a Secret clearance",
            page_number=1,
            is_blocker=True,
        ),
        _req(
            type="bonding",
            title="Bid bond",
            confidence="high",
            evidence_snippet="Bid bond required: 5% of total bid amount",
            page_number=2,
        ),
    ]
    out = await extract_requirements(
        ExtractInput(parsed=parsed, requirements=requirements)
    )

    assert len(out["requirements"]) == 2
    assert out["requirements"][0]["confidence"] == "high"
    assert out["requirements"][0]["is_blocker"] is True


async def test_out_of_range_page_number_is_nulled_and_downgraded() -> None:
    parsed = _make_parsed([(1, "Page one body text.")])
    out = await extract_requirements(
        ExtractInput(
            parsed=parsed,
            requirements=[
                _req(
                    type="deadline",
                    title="Submission deadline",
                    confidence="high",
                    evidence_snippet="Page one body text",
                    page_number=99,  # out of range
                )
            ],
        )
    )
    req = out["requirements"][0]
    assert req["page_number"] is None
    assert req["confidence"] == "low"


async def test_high_confidence_without_evidence_is_downgraded() -> None:
    parsed = _make_parsed([(1, "Some real source text on page one.")])
    out = await extract_requirements(
        ExtractInput(
            parsed=parsed,
            requirements=[
                _req(
                    type="technical",
                    title="SOC tier 2 staffing",
                    confidence="high",
                    evidence_snippet="",  # missing
                    page_number=1,
                )
            ],
        )
    )
    assert out["requirements"][0]["confidence"] == "low"


async def test_fabricated_snippet_is_downgraded() -> None:
    """A 'high' confidence snippet that doesn't appear (or fuzzy-match)
    anywhere in the source should be downgraded — hallucination guard."""
    parsed = _make_parsed(
        [(1, "The contractor shall deliver weekly status reports.")]
    )
    out = await extract_requirements(
        ExtractInput(
            parsed=parsed,
            requirements=[
                _req(
                    type="security",
                    title="Top Secret clearance",
                    confidence="high",
                    evidence_snippet=(
                        "All staff must hold a Top Secret with SCI eligibility "
                        "verified by the program office prior to onboarding"
                    ),
                    page_number=1,
                    is_blocker=True,
                )
            ],
        )
    )
    req = out["requirements"][0]
    assert req["confidence"] == "low"
    assert req["is_blocker"] is True  # downgrade only touches confidence


async def test_low_confidence_pass_through_unchanged() -> None:
    """Low/unknown confidence is not subject to the §11 downgrade logic."""
    parsed = _make_parsed([(1, "Some text.")])
    out = await extract_requirements(
        ExtractInput(
            parsed=parsed,
            requirements=[
                _req(
                    type="pricing",
                    title="Contract type",
                    confidence="low",
                    evidence_snippet="",
                    page_number=None,
                )
            ],
        )
    )
    assert out["requirements"][0]["confidence"] == "low"  # unchanged


# ─── Unparseable input ─────────────────────────────────────────────────────


async def test_unparseable_input_returns_empty_with_marker() -> None:
    unparseable = ParsePdfOutput(
        doc_id="image-only", page_count=2, unparseable=True, chunks=[]
    )
    out = await extract_requirements(ExtractInput(parsed=unparseable))
    assert out["chunks"] == []
    assert out["requirements"] == []
    assert out["missing_fields"] == ["all"]


# ─── Dict input compat ─────────────────────────────────────────────────────


async def test_dict_input_accepted() -> None:
    parsed = _make_parsed([(1, "Hello.")])
    out = await extract_requirements(
        {"parsed": parsed.model_dump(), "opportunity_metadata": {}}
    )
    assert "chunks" in out
    assert out["requirements"] == []
