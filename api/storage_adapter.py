"""Adapter that exposes api.storage's module-level functions as the
`_Storage` Protocol that fetch_attachment expects (an object with
`.upload(path, body) -> str`).
"""
from __future__ import annotations

from api import storage


class StorageAdapter:
    async def upload(self, path: str, body: bytes) -> str:
        return await storage.upload_bytes(
            path, body, content_type="application/pdf"
        )
