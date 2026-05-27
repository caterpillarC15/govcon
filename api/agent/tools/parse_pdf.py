from __future__ import annotations

from pathlib import Path
import string

import pypdf
from pydantic import BaseModel

UNPARSEABLE_THRESHOLD_CHARS = 50
MAX_CHUNK_CHARS = 12_000


class ParsedChunk(BaseModel):
    page_number: int
    text: str
    char_count: int


class ParsedPdf(BaseModel):
    doc_id: str
    page_count: int
    unparseable: bool
    chunks: list[ParsedChunk]


def _clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    printable = set(string.printable) | {"\n", "\t", "\r"}
    if text:
        non_printable = sum(1 for ch in text if ch not in printable and not ch.isprintable())
        if non_printable / max(len(text), 1) > 0.5:
            return ""
    return "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()


def _split_long_page(page_number: int, text: str) -> list[ParsedChunk]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [ParsedChunk(page_number=page_number, text=text, char_count=len(text))]
    chunks: list[ParsedChunk] = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    current = ""
    for paragraph in paragraphs or [text]:
        if current and len(current) + len(paragraph) + 2 > MAX_CHUNK_CHARS:
            chunks.append(ParsedChunk(page_number=page_number, text=current, char_count=len(current)))
            current = paragraph
        else:
            current = paragraph if not current else current + "\n\n" + paragraph
    if current:
        chunks.append(ParsedChunk(page_number=page_number, text=current, char_count=len(current)))
    return chunks


def parse_pdf(path: Path | str, doc_id: str | None = None) -> ParsedPdf:
    path = Path(path)
    doc_id = doc_id or path.stem
    try:
        reader = pypdf.PdfReader(str(path))
        page_count = len(reader.pages)
        chunks: list[ParsedChunk] = []
        for page_num, page in enumerate(reader.pages, start=1):
            text = _clean_text(page.extract_text() or "")
            if len(text) < 10:
                continue
            chunks.extend(_split_long_page(page_num, text))
    except Exception:
        return ParsedPdf(doc_id=doc_id, page_count=0, unparseable=True, chunks=[])

    total_chars = sum(chunk.char_count for chunk in chunks)
    unparseable = total_chars < UNPARSEABLE_THRESHOLD_CHARS
    return ParsedPdf(
        doc_id=doc_id,
        page_count=page_count,
        unparseable=unparseable,
        chunks=[] if unparseable else chunks,
    )
