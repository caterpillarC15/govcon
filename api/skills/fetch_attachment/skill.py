"""fetch_attachment — download a PDF from a URL and persist to Supabase Storage.

Used by Hermes Capture Analyst (T4.x) when a solicitation has an attachment URL but
the PDF is not yet local. Stores at raw/<run_id>/<filename> per PRD §7.5 storage layout.

NOT an LLM skill — pure HTTP + storage bridging.
"""
from __future__ import annotations
from typing import Any, Protocol
from urllib.parse import urlparse
import httpx


class _Storage(Protocol):
    """Minimal storage protocol — covers both real StorageClient and test doubles."""
    async def upload(self, path: str, body: bytes) -> str: ...


async def fetch_attachment(
    payload: dict[str, Any],
    *,
    storage: _Storage,
    http: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Download a URL and persist body to Supabase Storage.

    Input shape:
        {
          "run_id": str,        # UUID string of the agent run
          "url": str,           # http(s):// URL to the PDF
          "filename": str | None,  # optional override; derived from URL path if absent
        }

    Output:
        {
          "storage_path": str,        # e.g. "raw/abc-123/RFP-001.pdf"
          "bytes_downloaded": int,
        }

    Raises httpx.HTTPError on network failure / non-2xx (Hermes runner handles
    recovery per §4.5; this skill does not silently swallow).
    """
    run_id = payload["run_id"]
    url = payload["url"]
    filename = payload.get("filename") or _derive_filename(url)
    path = f"raw/{run_id}/{filename}"

    owns_client = http is None
    client = http or httpx.AsyncClient()
    try:
        resp = await client.get(url, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()
        body = resp.content
    finally:
        if owns_client:
            await client.aclose()

    await storage.upload(path, body)
    return {"storage_path": path, "bytes_downloaded": len(body)}


def _derive_filename(url: str) -> str:
    """Extract a filename from a URL's path; fall back to attachment.pdf."""
    parsed = urlparse(url).path
    name = parsed.rsplit("/", 1)[-1] or "attachment.pdf"
    return name if name.lower().endswith(".pdf") else f"{name}.pdf"
