"""Supabase Storage thin wrapper — replaces /var/lib/govcapture/{raw,parsed} on the VX1.

Uses the Storage REST API directly via httpx (we already depend on httpx; no need
for the heavier `supabase` Python SDK). Authenticated with the service-role key,
which bypasses RLS — server-side only, never leaked to the browser.

Bucket layout (per PRD v1.2.3 §7.5):

    raw/<run_id>/<filename>           — original PDFs (live SAM fetch + uploads)
    parsed/<run_id>/<doc_id>.json     — parse_pdf chunks + metadata
    fixtures/<slug>/...               — seeded fixture PDFs mirrored to bucket

Skills (parse_pdf, extract_requirements) keep taking local paths; the Hermes
toolset wrapper / eval harness downloads from Storage to /tmp first.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from api.config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised for any non-2xx Supabase Storage response we can't recover from."""


def _base_url() -> str:
    if not settings.supabase_url:
        raise StorageError("SUPABASE_URL is not configured")
    return settings.supabase_url.rstrip("/")


def _headers(content_type: str | None = None) -> dict[str, str]:
    if not settings.supabase_service_role_key:
        raise StorageError("SUPABASE_SERVICE_ROLE_KEY is not configured")
    h = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


def _object_url(key: str) -> str:
    return f"{_base_url()}/storage/v1/object/{settings.supabase_storage_bucket}/{key.lstrip('/')}"


async def upload_bytes(
    key: str,
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
    upsert: bool = True,
) -> str:
    """Upload `data` to `bucket/key`. Returns the storage URI (`supabase://bucket/key`)."""
    headers = _headers(content_type)
    headers["x-upsert"] = "true" if upsert else "false"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(_object_url(key), content=data, headers=headers)
    if resp.status_code >= 300:
        raise StorageError(
            f"Supabase upload failed: {resp.status_code} {resp.text} (key={key})"
        )
    return f"supabase://{settings.supabase_storage_bucket}/{key.lstrip('/')}"


async def upload_file(local_path: Path, key: str, *, content_type: str | None = None) -> str:
    if content_type is None:
        suffix = local_path.suffix.lower()
        content_type = {
            ".pdf": "application/pdf",
            ".json": "application/json",
            ".txt": "text/plain",
        }.get(suffix, "application/octet-stream")
    return await upload_bytes(
        key, local_path.read_bytes(), content_type=content_type, upsert=True
    )


async def download_bytes(key: str) -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(_object_url(key), headers=_headers())
    if resp.status_code == 404:
        raise StorageError(f"Supabase object not found: {key}")
    if resp.status_code >= 300:
        raise StorageError(
            f"Supabase download failed: {resp.status_code} {resp.text} (key={key})"
        )
    return resp.content


async def download_to_tmp(key: str, *, dest_dir: Path | None = None) -> Path:
    """Download `key` to a local file under `dest_dir` (default `/tmp`).

    Used by the eval harness and the Hermes `fetch_attachment` bridge to feed
    `parse_pdf`, which still expects a local path.
    """
    target_dir = dest_dir or Path("/tmp")
    target_dir.mkdir(parents=True, exist_ok=True)
    local_path = target_dir / Path(key).name
    local_path.write_bytes(await download_bytes(key))
    return local_path


async def delete(key: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(_object_url(key), headers=_headers())
    if resp.status_code not in (200, 204, 404):
        raise StorageError(
            f"Supabase delete failed: {resp.status_code} {resp.text} (key={key})"
        )
