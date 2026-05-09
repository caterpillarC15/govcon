"""parse_pdf — deterministic page-aware PDF text extraction (PRD §5.5, §17 Q2).

No OCR. Image-only PDFs are reported as `unparseable=True`. Fonts that produce
mostly-non-printable garbage are treated as empty for that page.

Skill registration: per the 2026-05-09 decision, this module is invoked directly
as plain Python from the FastAPI proxy and the eval harness; the Hermes
toolset wrapper is added in A9.
"""
from __future__ import annotations

import logging
import string
from pathlib import Path
from typing import Any

import pypdf
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

UNPARSEABLE_TOTAL_CHARS = 50
"""Whole-doc threshold below which we mark the PDF unparseable (PRD §17 Q2)."""

PAGE_PRINTABLE_RATIO = 0.5
"""A page whose extract is <50% printable ASCII is treated as empty
(custom-font garbage)."""

PAGE_MIN_CHARS = 10
"""A page extract below this length is treated as empty (custom-font / image)."""

PRINTABLE = set(string.printable)


class ParsedChunk(BaseModel):
    page_number: int = Field(..., ge=1)
    text: str
    char_count: int


class ParsePdfInput(BaseModel):
    path: str
    doc_id: str | None = None


class ParsePdfOutput(BaseModel):
    doc_id: str
    page_count: int
    unparseable: bool
    chunks: list[ParsedChunk]
    error: str | None = None


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    keep = sum(1 for ch in text if ch in PRINTABLE)
    return keep / len(text)


def _page_is_meaningful(text: str) -> bool:
    if len(text) < PAGE_MIN_CHARS:
        return False
    return _printable_ratio(text) >= PAGE_PRINTABLE_RATIO


def parse_pdf(payload: ParsePdfInput | dict[str, Any]) -> ParsePdfOutput:
    """Extract per-page text from a PDF.

    Returns `unparseable=True` (and empty `chunks`) when the file is missing,
    encrypted, or yields less than `UNPARSEABLE_TOTAL_CHARS` of text across all
    pages — that's the trigger for the planner's degraded-recovery branch.
    """
    if isinstance(payload, dict):
        payload = ParsePdfInput.model_validate(payload)

    path = Path(payload.path)
    doc_id = payload.doc_id or path.stem

    if not path.exists():
        logger.warning("parse_pdf: file not found at %s", path)
        return ParsePdfOutput(
            doc_id=doc_id,
            page_count=0,
            unparseable=True,
            chunks=[],
            error="file_not_found",
        )

    try:
        reader = pypdf.PdfReader(str(path))
    except pypdf.errors.FileNotDecryptedError:
        logger.warning("parse_pdf: encrypted PDF at %s — marking unparseable", path)
        return ParsePdfOutput(
            doc_id=doc_id,
            page_count=0,
            unparseable=True,
            chunks=[],
            error="encrypted",
        )
    except (pypdf.errors.PdfReadError, OSError) as exc:
        logger.warning("parse_pdf: read error for %s: %s", path, exc)
        return ParsePdfOutput(
            doc_id=doc_id,
            page_count=0,
            unparseable=True,
            chunks=[],
            error="read_error",
        )

    page_count = len(reader.pages)
    chunks: list[ParsedChunk] = []
    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception:  # noqa: BLE001 -- pypdf raises a wide variety on malformed pages
            text = ""
        if not _page_is_meaningful(text):
            continue
        chunks.append(ParsedChunk(page_number=page_num, text=text, char_count=len(text)))

    total_chars = sum(c.char_count for c in chunks)
    unparseable = total_chars < UNPARSEABLE_TOTAL_CHARS

    return ParsePdfOutput(
        doc_id=doc_id,
        page_count=page_count,
        unparseable=unparseable,
        chunks=[] if unparseable else chunks,
    )
