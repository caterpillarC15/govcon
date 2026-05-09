"""load_seeded_opportunities — fixture loader integration tests.

Hits the live local Postgres. Each test cleans up its own rows.
Skips automatically if the DB isn't reachable.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.config import settings
from api.db.models import Opportunity
from api.skills.load_seeded_opportunities import load_seeded_opportunities

_ALL_FIXTURE_SLUGS = {"strong-pursue", "maybe", "reject", "adversarial-image-pdf"}


@pytest_asyncio.fixture
async def db_session():
    """Per-test async session with NullPool — avoids event-loop conflicts between tests."""
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    Maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with Maker() as s:
            yield s
    except Exception as exc:  # pragma: no cover — DB unreachable
        pytest.skip(f"DB unreachable: {exc}")
    finally:
        await engine.dispose()


async def _cleanup(session, slugs: set[str]) -> None:
    """Delete all opportunities whose slug is in the given set."""
    await session.execute(delete(Opportunity).where(Opportunity.slug.in_(slugs)))
    await session.commit()


async def test_loads_all_four_fixtures(db_session) -> None:
    try:
        out = await load_seeded_opportunities({"slugs": None}, session=db_session)
        slugs = {o["slug"] for o in out["opportunities"]}
        assert slugs == _ALL_FIXTURE_SLUGS
        assert len(out["opportunities"]) == 4
        for opp in out["opportunities"]:
            assert "id" in opp
            assert "title" in opp
    finally:
        await _cleanup(db_session, _ALL_FIXTURE_SLUGS)


async def test_loads_specific_subset(db_session) -> None:
    try:
        out = await load_seeded_opportunities({"slugs": ["strong-pursue"]}, session=db_session)
        assert len(out["opportunities"]) == 1
        assert out["opportunities"][0]["slug"] == "strong-pursue"
    finally:
        await _cleanup(db_session, {"strong-pursue"})


async def test_idempotent_on_repeat(db_session) -> None:
    """Loading the same slug twice must return the same row, not create a duplicate."""
    try:
        a = await load_seeded_opportunities({"slugs": ["maybe"]}, session=db_session)
        b = await load_seeded_opportunities({"slugs": ["maybe"]}, session=db_session)
        assert len(a["opportunities"]) == 1
        assert len(b["opportunities"]) == 1
        assert a["opportunities"][0]["id"] == b["opportunities"][0]["id"]
    finally:
        await _cleanup(db_session, {"maybe"})


async def test_skips_template_directory(db_session, tmp_path) -> None:
    """Template directories (starting with '_') MUST be skipped."""
    fixtures_dir = tmp_path / "fixtures"
    template = fixtures_dir / "_template"
    template.mkdir(parents=True)
    (template / "manifest.json").write_text(
        json.dumps({"slug": "should-not-load", "opportunity": {}})
    )

    out = await load_seeded_opportunities(
        {"slugs": None}, session=db_session, fixtures_dir=fixtures_dir
    )
    assert out["opportunities"] == []
