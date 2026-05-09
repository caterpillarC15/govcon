"""load_seeded_opportunities — read /fixtures/*/manifest.json, persist to opportunities table.

Idempotent on slug: if an opportunity with the same slug already exists, return the existing
row instead of creating a duplicate. Skips fixture directories starting with '_' or '.' (templates).

The top-level manifest slug (= directory name, e.g. "strong-pursue") is used as the canonical
slug stored in the DB. The inner opportunity.slug field is overwritten by this value.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.opportunity import OpportunityRepository

logger = logging.getLogger(__name__)

DEFAULT_FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures"

# Fields managed automatically by the ORM / DB — strip them from the manifest payload.
_AUTO_FIELDS = frozenset({"id", "created_at", "updated_at"})

# Date fields in the opportunity block that asyncpg won't coerce from str automatically.
_DATE_FIELDS = frozenset({"due_date", "posted_date"})


async def load_seeded_opportunities(
    payload: dict[str, Any],
    *,
    session: AsyncSession,
    fixtures_dir: Path | None = None,
) -> dict[str, Any]:
    """Read fixture manifests and persist opportunities to the DB.

    Input:
        {"slugs": list[str] | None}  — None means load all fixtures

    Output:
        {"opportunities": list[dict]}  — each dict has id (str UUID), slug, title
    """
    fixtures_dir = fixtures_dir or DEFAULT_FIXTURES_DIR
    requested_slugs: list[str] | None = payload.get("slugs")

    repo = OpportunityRepository(session)
    loaded: list[dict] = []

    for manifest_path in _discover_manifests(fixtures_dir, requested_slugs):
        manifest = json.loads(manifest_path.read_text())
        # The top-level slug is the canonical identifier (= directory name).
        slug = manifest["slug"]

        existing = await repo.get_by_slug(slug)
        if existing is not None:
            logger.debug("load_seeded_opportunities: slug %r already exists, skipping insert", slug)
            loaded.append({"id": str(existing.id), "slug": existing.slug, "title": existing.title})
            continue

        opp_dict: dict[str, Any] = dict(manifest["opportunity"])
        # Overwrite with the canonical top-level slug.
        opp_dict["slug"] = slug
        # Strip auto-managed fields.
        for field in _AUTO_FIELDS:
            opp_dict.pop(field, None)
        # Coerce ISO date strings to date objects (asyncpg requires native date, not str).
        for field in _DATE_FIELDS:
            val = opp_dict.get(field)
            if isinstance(val, str):
                opp_dict[field] = date.fromisoformat(val)

        opp = await repo.create(opp_dict)
        logger.info("load_seeded_opportunities: created opportunity slug=%r id=%s", slug, opp.id)
        loaded.append({"id": str(opp.id), "slug": opp.slug, "title": opp.title})

    return {"opportunities": loaded}


def _discover_manifests(fixtures_dir: Path, requested_slugs: list[str] | None) -> list[Path]:
    """Return sorted manifest paths, skipping template directories."""
    if not fixtures_dir.exists():
        return []

    paths: list[Path] = []
    for child in sorted(fixtures_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("_") or child.name.startswith("."):
            continue
        if requested_slugs is not None and child.name not in requested_slugs:
            continue
        manifest = child / "manifest.json"
        if manifest.exists():
            paths.append(manifest)
    return paths
