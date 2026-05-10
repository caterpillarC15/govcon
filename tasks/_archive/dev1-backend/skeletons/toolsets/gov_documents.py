"""gov_documents toolset — Capture Analyst's tools.

Solicitation document fetching and parsing. Hermes' built-in `web` toolset
covers fetch_attachment and verify_source_page in some configurations; check
during the A9 spike whether to vendor or rely on built-ins.
"""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING


# ─── fetch_attachment ───────────────────────────────────────────────────────
# A10 was originally OpenClaw; per PRD v1.2.2, Hermes' built-in browser/HTTP
# tools cover this. Vendor a wrapper if Hermes' built-ins are insufficient
# (e.g., portals requiring session cookies).

async def fetch_attachment(url: str) -> dict:
    """Download a solicitation attachment. Returns {local_path, content_type, bytes}.

    Hermes' built-in web tools handle most cases. If a portal requires session
    cookies or login, A9-spike decides whether to vendor a Playwright-based
    skill via Hermes' skill mechanism.

    Retries: once on transient network failure. Then degrades (returns {error, ...}).
    """
    raise NotImplementedError("A10 (Hermes built-in or vendored) — confirmed during A9 spike")


# ─── parse_pdf ──────────────────────────────────────────────────────────────
# A4 — pure Python, no LLM, no external deps beyond pypdf

def parse_pdf(path: str | Path, doc_id: str | None = None) -> dict:
    """Extract page-level text from a PDF.

    Returns: {doc_id, page_count, unparseable: bool, chunks: [{page_number, text, char_count}]}

    Behavior:
        - Iterate pages with pypdf.PdfReader.
        - Total chars < 50 → unparseable=True, chunks=[].
        - Per-page chunking. Sub-chunk pages > ~3000 tokens at paragraph boundaries.
        - Don't OCR (PRD §17 Q2: out of scope).
        - Encrypted PDFs → unparseable=True.

    Cost: $0 (pure local).

    See: tasks/dev1-backend/tasks/A4.md
    """
    raise NotImplementedError("A4 — Dev 1 implements parse_pdf with pypdf")


# ─── verify_source_page ─────────────────────────────────────────────────────
# Used sparingly when SAM API metadata is incomplete or contradictory.

async def verify_source_page(url: str, fields_to_verify: list[str]) -> dict:
    """Visit a source page (e.g., SAM.gov opportunity page) and confirm fields.

    Returns: {verified: bool, fields: {<field>: <value>}}

    Hermes' browser tools handle the rendering. We verify selected fields
    (deadline, set-aside, NAICS) when the API response was partial.

    Use sparingly — adds latency and is a fragile path.
    """
    raise NotImplementedError("A10 (Hermes built-in or vendored) — confirmed during A9 spike")
