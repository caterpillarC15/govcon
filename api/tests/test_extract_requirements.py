"""Mocked tests for the extract_requirements skill.

The LLM is replaced with a fake that returns canned JSON. Tests verify:
- Schema parsing of the §10.1 output shape.
- Post-validation rules: page-bounds, evidence binding, fuzzy-match downgrade.
- Unparseable input returns empty output with no LLM call.
- LLM error path returns degraded output, not an exception.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from api.llm import LLM, LLMError, LLMMetrics
from api.skills.extract_requirements import (
    ExtractInput,
    RequirementExtractionOutput,
    extract_requirements,
)
from api.skills.parse_pdf import ParsedChunk, ParsePdfOutput


class FakeLLM(LLM):
    """Stand-in for `api.llm.LLM` — returns whatever JSON the test sets up."""

    def __init__(
        self,
        *,
        payload: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        # Skip parent __init__ — we don't want a real Anthropic client.
        self._client = None  # type: ignore[assignment]
        self._payload = payload
        self._raise = raise_exc
        self.calls: list[dict[str, Any]] = []

    async def complete_structured(  # type: ignore[override]
        self,
        *,
        system: str,
        user: str,
        output_model: type[BaseModel],
        model: str | None = None,
        max_tokens: int = 4096,
        cache_system: bool = True,
    ):
        self.calls.append({"system": system, "user": user, "model": model})
        if self._raise is not None:
            raise self._raise
        assert self._payload is not None, "FakeLLM needs payload or raise_exc"
        parsed = output_model.model_validate(self._payload)
        metrics = LLMMetrics(
            model=model or "claude-haiku-4-5-20251001",
            latency_ms=42,
            cost_usd=0.0001,
            input_tokens=1500,
            output_tokens=200,
        )
        return parsed, metrics


def _make_parsed(chunks: list[tuple[int, str]]) -> ParsePdfOutput:
    return ParsePdfOutput(
        doc_id="RFP-test",
        page_count=max(p for p, _ in chunks) if chunks else 0,
        unparseable=False,
        chunks=[ParsedChunk(page_number=p, text=t, char_count=len(t)) for p, t in chunks],
    )


# ─── Happy path ────────────────────────────────────────────────────────────


async def test_extract_returns_validated_payload_unchanged() -> None:
    parsed = _make_parsed(
        [
            (1, "Personnel must hold a Secret clearance prior to award."),
            (2, "Bid bond required: 5% of total bid amount."),
        ]
    )
    canned = {
        "requirements": [
            {
                "type": "security",
                "title": "Secret clearance",
                "value": "Secret",
                "description": "All key personnel must hold a Secret clearance.",
                "confidence": "high",
                "evidence_snippet": "Personnel must hold a Secret clearance",
                "source_document": "RFP-test",
                "page_number": 1,
                "is_blocker": True,
            },
            {
                "type": "bonding",
                "title": "Bid bond",
                "value": "5%",
                "description": "Bid bond at 5% of bid amount.",
                "confidence": "high",
                "evidence_snippet": "Bid bond required: 5% of total bid amount",
                "source_document": "RFP-test",
                "page_number": 2,
                "is_blocker": False,
            },
        ],
        "missing_fields": ["pricing"],
        "conflicts": [],
    }
    fake = FakeLLM(payload=canned)

    out, metrics = await extract_requirements(
        ExtractInput(parsed=parsed, opportunity_metadata={"title": "Test"}),
        llm=fake,
    )

    assert isinstance(out, RequirementExtractionOutput)
    assert len(out.requirements) == 2
    assert out.requirements[0].confidence == "high"  # snippet matches → kept
    assert out.requirements[0].is_blocker is True
    assert out.missing_fields == ["pricing"]
    assert metrics.cost_usd > 0
    assert len(fake.calls) == 1


# ─── Post-validation: page bounds ──────────────────────────────────────────


async def test_out_of_range_page_number_is_nulled_and_downgraded() -> None:
    parsed = _make_parsed([(1, "Page one body text.")])
    canned = {
        "requirements": [
            {
                "type": "deadline",
                "title": "Submission deadline",
                "value": "May 30 2026",
                "description": "Proposals due 5 PM EST.",
                "confidence": "high",
                "evidence_snippet": "Page one body text",
                "source_document": "RFP-test",
                "page_number": 99,  # out of range → null + downgrade
                "is_blocker": False,
            }
        ],
        "missing_fields": [],
        "conflicts": [],
    }
    out, _ = await extract_requirements(
        ExtractInput(parsed=parsed), llm=FakeLLM(payload=canned)
    )
    req = out.requirements[0]
    assert req.page_number is None
    assert req.confidence == "low"


# ─── Post-validation: evidence binding ─────────────────────────────────────


async def test_high_confidence_without_evidence_is_downgraded() -> None:
    parsed = _make_parsed([(1, "Some real source text on page one.")])
    canned = {
        "requirements": [
            {
                "type": "technical",
                "title": "SOC tier 2 staffing",
                "value": "24/7",
                "description": "Continuous SOC coverage.",
                "confidence": "high",
                "evidence_snippet": "",  # missing
                "source_document": "RFP-test",
                "page_number": 1,
                "is_blocker": False,
            }
        ],
        "missing_fields": [],
        "conflicts": [],
    }
    out, _ = await extract_requirements(
        ExtractInput(parsed=parsed), llm=FakeLLM(payload=canned)
    )
    assert out.requirements[0].confidence == "low"


async def test_fabricated_snippet_is_downgraded() -> None:
    """A 'high' confidence snippet that doesn't appear (or fuzzy-match) anywhere
    in the source should be downgraded — this is the hallucination guard."""
    parsed = _make_parsed([(1, "The contractor shall deliver weekly status reports.")])
    canned = {
        "requirements": [
            {
                "type": "security",
                "title": "Top Secret clearance",
                "value": "Top Secret/SCI",
                "description": "TS/SCI required.",
                "confidence": "high",
                "evidence_snippet": (
                    "All staff must hold a Top Secret with SCI eligibility "
                    "verified by the program office prior to onboarding"
                ),
                "source_document": "RFP-test",
                "page_number": 1,
                "is_blocker": True,
            }
        ],
        "missing_fields": [],
        "conflicts": [],
    }
    out, _ = await extract_requirements(
        ExtractInput(parsed=parsed), llm=FakeLLM(payload=canned)
    )
    req = out.requirements[0]
    assert req.confidence == "low"
    assert req.is_blocker is True  # downgrade only touches confidence


async def test_low_confidence_pass_through_unchanged() -> None:
    """Low/unknown confidence requirements are not subject to the evidence-binding
    or fuzzy-match downgrade logic — they're already 'low'."""
    parsed = _make_parsed([(1, "Some text.")])
    canned = {
        "requirements": [
            {
                "type": "pricing",
                "title": "Contract type",
                "value": "Possibly FFP",
                "description": "Unclear from the document.",
                "confidence": "low",
                "evidence_snippet": "",
                "source_document": "RFP-test",
                "page_number": None,
                "is_blocker": False,
            }
        ],
        "missing_fields": ["pricing.type"],
        "conflicts": [],
    }
    out, _ = await extract_requirements(
        ExtractInput(parsed=parsed), llm=FakeLLM(payload=canned)
    )
    assert out.requirements[0].confidence == "low"  # unchanged


# ─── Unparseable input + LLM failure ───────────────────────────────────────


async def test_unparseable_input_skips_llm() -> None:
    unparseable = ParsePdfOutput(
        doc_id="image-only", page_count=2, unparseable=True, chunks=[]
    )
    fake = FakeLLM(payload={"requirements": [], "missing_fields": [], "conflicts": []})

    out, metrics = await extract_requirements(
        ExtractInput(parsed=unparseable), llm=fake
    )
    assert out.requirements == []
    assert out.missing_fields == ["all"]
    assert metrics.cost_usd == 0.0
    assert metrics.latency_ms == 0
    assert metrics.attempts == 0
    assert fake.calls == []  # LLM never invoked


async def test_llm_error_returns_degraded_output() -> None:
    parsed = _make_parsed([(1, "Real text.")])
    fake = FakeLLM(raise_exc=LLMError("API key invalid"))

    out, metrics = await extract_requirements(
        ExtractInput(parsed=parsed), llm=fake
    )
    assert out.requirements == []
    assert out.missing_fields == ["all"]
    assert metrics.cost_usd == 0.0
    assert len(fake.calls) == 1  # tried once, failed gracefully


async def test_dict_input_accepted() -> None:
    parsed = _make_parsed([(1, "Hello.")])
    fake = FakeLLM(payload={"requirements": [], "missing_fields": [], "conflicts": []})
    out, _ = await extract_requirements(
        {"parsed": parsed.model_dump(), "opportunity_metadata": {}}, llm=fake
    )
    assert isinstance(out, RequirementExtractionOutput)
