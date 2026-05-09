"""Unit tests for the parse_pdf skill.

Generates test PDFs on the fly with reportlab so the suite is hermetic and
doesn't depend on Dev 2's fixture content. Fixture-dependent tests against
/fixtures/<slug>/attachments/*.pdf gracefully skip when the files aren't there.
"""
from __future__ import annotations

from pathlib import Path

import pytest

reportlab = pytest.importorskip(
    "reportlab",
    reason="reportlab not installed; install with `uv pip install reportlab` for hermetic PDF tests.",
)
from reportlab.lib.pagesizes import LETTER  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from api.skills.parse_pdf import ParsePdfInput, parse_pdf  # noqa: E402

FIXTURES_ROOT = Path(__file__).resolve().parents[2] / "fixtures"


def _make_text_pdf(path: Path, pages: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=LETTER)
    for page_text in pages:
        y = 750
        for line in page_text.splitlines() or [page_text]:
            c.drawString(72, y, line)
            y -= 14
        c.showPage()
    c.save()


def _make_blank_pdf(path: Path, n_pages: int = 1) -> None:
    c = canvas.Canvas(str(path), pagesize=LETTER)
    for _ in range(n_pages):
        c.showPage()
    c.save()


def test_simple_two_page_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    _make_text_pdf(
        pdf,
        [
            "RFP-2026-001\nSecret clearance required.\nDeadline: 2026-07-01.",
            "Past performance: three federal cybersecurity contracts within five years.",
        ],
    )

    out = parse_pdf(ParsePdfInput(path=str(pdf)))

    assert out.doc_id == "doc"
    assert out.page_count == 2
    assert out.unparseable is False
    assert len(out.chunks) == 2
    assert out.chunks[0].page_number == 1
    assert out.chunks[1].page_number == 2
    assert "Secret clearance" in out.chunks[0].text
    assert all(c.char_count == len(c.text) for c in out.chunks)


def test_blank_pdf_marked_unparseable(tmp_path: Path) -> None:
    pdf = tmp_path / "blank.pdf"
    _make_blank_pdf(pdf, n_pages=2)

    out = parse_pdf(ParsePdfInput(path=str(pdf)))

    assert out.page_count == 2
    assert out.unparseable is True
    assert out.chunks == []


def test_missing_file_marked_unparseable(tmp_path: Path) -> None:
    out = parse_pdf(ParsePdfInput(path=str(tmp_path / "nope.pdf")))
    assert out.unparseable is True
    assert out.chunks == []
    assert out.error == "file_not_found"


def test_doc_id_override(tmp_path: Path) -> None:
    pdf = tmp_path / "raw.pdf"
    _make_text_pdf(pdf, ["A solicitation document with enough text to clear the threshold."])
    out = parse_pdf(ParsePdfInput(path=str(pdf), doc_id="strong-pursue/RFP-001"))
    assert out.doc_id == "strong-pursue/RFP-001"


def test_dict_input_accepted(tmp_path: Path) -> None:
    """Convenience: callers (eval harness, Hermes bridge) may pass a dict."""
    pdf = tmp_path / "d.pdf"
    _make_text_pdf(pdf, ["Some content beyond fifty characters total to clear the threshold."])
    out = parse_pdf({"path": str(pdf)})
    assert out.unparseable is False


def test_short_extract_marked_unparseable(tmp_path: Path) -> None:
    """A page with < 50 chars total is below the threshold and should be unparseable."""
    pdf = tmp_path / "short.pdf"
    _make_text_pdf(pdf, ["hi"])
    out = parse_pdf(ParsePdfInput(path=str(pdf)))
    assert out.unparseable is True
    assert out.chunks == []


# ─── Fixture-dependent tests (skip until Dev 2 lands the seed PDFs) ────────


def _fixture_path(slug: str) -> Path:
    return FIXTURES_ROOT / slug / "attachments"


def _has_pdfs(slug: str) -> bool:
    p = _fixture_path(slug)
    return p.is_dir() and any(p.glob("*.pdf"))


@pytest.mark.skipif(not _has_pdfs("strong-pursue"), reason="Dev 2 fixture not yet present")
def test_strong_pursue_fixture_parses() -> None:
    pdf = next(_fixture_path("strong-pursue").glob("*.pdf"))
    out = parse_pdf(ParsePdfInput(path=str(pdf)))
    assert not out.unparseable
    assert out.page_count >= 1
    assert sum(c.char_count for c in out.chunks) > 200
    assert all(c.page_number > 0 for c in out.chunks)


@pytest.mark.skipif(
    not _has_pdfs("adversarial-image-pdf"), reason="Dev 2 fixture not yet present"
)
def test_adversarial_image_pdf_unparseable() -> None:
    pdf = next(_fixture_path("adversarial-image-pdf").glob("*.pdf"))
    out = parse_pdf(ParsePdfInput(path=str(pdf)))
    assert out.unparseable
    assert out.chunks == []
