"""Live-DB smoke test that the SQLAlchemy models round-trip against the migrated schema.

Hits the local `govcon` Postgres (per A1/A2). Each test cleans up its own rows.
Skips automatically if the DB isn't reachable.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.config import settings
from api.db.models import CompanyProfile, Opportunity


@pytest_asyncio.fixture
async def session():
    """Per-test engine with NullPool — pytest-asyncio creates a fresh event loop per test,
    and a pooled connection from a prior loop will fail with "Event loop is closed"."""
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    Maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with Maker() as s:
            yield s
    except Exception as exc:  # pragma: no cover -- DB unreachable
        pytest.skip(f"DB unreachable: {exc}")
    finally:
        await engine.dispose()


async def test_company_profile_round_trip(session) -> None:
    profile = CompanyProfile(
        id=uuid.uuid4(),
        name="Test Co",
        capabilities=["cyber"],
        industry_keywords=["soc"],
        naics_codes=["541512"],
        certifications=["CMMC L2"],
        small_business_status=True,
        past_performance=[{"title": "demo", "agency": "GSA"}],
        service_area=["TX"],
        preferred_role="either",
    )
    session.add(profile)
    await session.commit()

    result = await session.execute(select(CompanyProfile).where(CompanyProfile.id == profile.id))
    fetched = result.scalar_one()
    try:
        assert fetched.name == "Test Co"
        assert fetched.capabilities == ["cyber"]
        assert fetched.small_business_status is True
        assert fetched.created_at is not None
    finally:
        await session.delete(fetched)
        await session.commit()


async def test_opportunity_cascade_deletes_requirements(session) -> None:
    """Deleting an opportunity must cascade to its requirements (PRD §8 cascade rules)."""
    from api.db.models import ExtractedRequirement

    opp = Opportunity(
        id=uuid.uuid4(),
        title="Test RFP",
        agency="Test Agency",
        solicitation_number="TEST-001",
        attachments=[],
    )
    session.add(opp)
    await session.commit()

    req = ExtractedRequirement(
        id=uuid.uuid4(),
        opportunity_id=opp.id,
        type="technical",
        title="Test req",
        confidence="high",
        is_blocker=False,
    )
    session.add(req)
    await session.commit()

    await session.delete(opp)
    await session.commit()

    result = await session.execute(
        select(ExtractedRequirement).where(ExtractedRequirement.id == req.id)
    )
    assert result.scalar_one_or_none() is None
