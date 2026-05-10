"""fetch_attachment — happy path + filename derivation + error propagation."""
from __future__ import annotations
import httpx
import pytest
import respx
from api.skills.fetch_attachment import fetch_attachment


class _FakeStorage:
    """Captures upload calls for assertion."""
    def __init__(self) -> None:
        self.uploaded: list[tuple[str, bytes]] = []

    async def upload(self, path: str, body: bytes) -> str:
        self.uploaded.append((path, body))
        return path


async def test_downloads_and_uploads_to_storage():
    pdf_bytes = b"%PDF-1.4\n%test content"
    async with respx.mock(base_url="https://example.gov") as router:
        router.get("/rfp.pdf").respond(200, content=pdf_bytes)
        storage = _FakeStorage()
        out = await fetch_attachment(
            {"run_id": "abc-123", "url": "https://example.gov/rfp.pdf"},
            storage=storage,
        )
    assert out["storage_path"] == "raw/abc-123/rfp.pdf"
    assert out["bytes_downloaded"] == len(pdf_bytes)
    assert storage.uploaded == [("raw/abc-123/rfp.pdf", pdf_bytes)]


async def test_filename_override():
    async with respx.mock(base_url="https://example.gov") as router:
        router.get("/some/path/document").respond(200, content=b"%PDF-1.4")
        storage = _FakeStorage()
        out = await fetch_attachment(
            {
                "run_id": "abc-123",
                "url": "https://example.gov/some/path/document",
                "filename": "Solicitation-Draft.pdf",
            },
            storage=storage,
        )
    assert out["storage_path"] == "raw/abc-123/Solicitation-Draft.pdf"


async def test_filename_derivation_appends_pdf_when_missing():
    async with respx.mock(base_url="https://example.gov") as router:
        router.get("/rfp_attachment").respond(200, content=b"%PDF-1.4")
        storage = _FakeStorage()
        out = await fetch_attachment(
            {"run_id": "run1", "url": "https://example.gov/rfp_attachment"},
            storage=storage,
        )
    assert out["storage_path"] == "raw/run1/rfp_attachment.pdf"


async def test_filename_derivation_root_url_fallback():
    """URL with no path component falls back to attachment.pdf."""
    async with respx.mock(base_url="https://example.gov") as router:
        router.get("/").respond(200, content=b"%PDF-1.4")
        storage = _FakeStorage()
        out = await fetch_attachment(
            {"run_id": "run1", "url": "https://example.gov/"},
            storage=storage,
        )
    assert out["storage_path"] == "raw/run1/attachment.pdf"


async def test_404_raises():
    """Non-2xx response propagates — recovery is the runner's job, not this skill's."""
    async with respx.mock(base_url="https://example.gov") as router:
        router.get("/missing.pdf").respond(404)
        storage = _FakeStorage()
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_attachment(
                {"run_id": "run1", "url": "https://example.gov/missing.pdf"},
                storage=storage,
            )
        # Storage was NOT touched
        assert storage.uploaded == []


async def test_follows_redirects():
    """Some SAM endpoints redirect to S3-signed URLs — must follow."""
    async with respx.mock() as router:
        router.get("https://example.gov/redirect.pdf").respond(
            302, headers={"Location": "https://cdn.example.gov/real.pdf"}
        )
        router.get("https://cdn.example.gov/real.pdf").respond(
            200, content=b"%PDF-1.4 redirected"
        )
        storage = _FakeStorage()
        out = await fetch_attachment(
            {"run_id": "run1", "url": "https://example.gov/redirect.pdf"},
            storage=storage,
        )
    assert out["bytes_downloaded"] == len(b"%PDF-1.4 redirected")
