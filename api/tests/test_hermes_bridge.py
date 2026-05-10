from __future__ import annotations

import json
import uuid
from typing import Any

import pytest

from api.agent.hermes_bridge import run_seeded_michaela_capture
from api.repositories.agent_run import AgentRunRepository
from api.repositories.company_profile import CompanyProfileRepository
from api.tests.conftest import TEST_USER_ID

pytestmark = pytest.mark.asyncio


class FakeRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, channel: str, message: str) -> None:
        self.published.append((channel, json.loads(message)))


async def test_seeded_michaela_bridge_persists_run_outputs(fake_supabase) -> None:
    profile_repo = CompanyProfileRepository(fake_supabase)
    run_repo = AgentRunRepository(fake_supabase)

    profile = await profile_repo.create(
        {
            "owner_profile_id": str(TEST_USER_ID),
            "name": "Lone Star CyberWorks",
            "capabilities": ["cloud migration", "cybersecurity"],
            "small_business_status": True,
            "naics_codes": ["541512"],
            "preferred_role": "either",
        }
    )
    run = await run_repo.create(
        goal="Find cybersecurity opportunities in the next 90 days",
        profile_id=TEST_USER_ID,
        company_profile_id=uuid.UUID(str(profile["id"])),
    )

    redis = FakeRedis()
    await run_seeded_michaela_capture(
        redis=redis,
        client=fake_supabase,
        run_id=uuid.UUID(str(run["id"])),
    )

    completed = await run_repo.get(uuid.UUID(str(run["id"])))
    assert completed is not None
    assert completed["status"] == "complete"
    assert len(completed["opportunities"]) == 4
    assert completed["selected_opportunity_id"] is not None
    assert completed["action_package_id"] is not None

    event_types = [event["type"] for _, event in redis.published]
    assert "run_started" in event_types
    assert "opportunity_ranked" in event_types
    assert event_types[-1] == "run_completed"

    tools = [
        event["tool"]
        for _, event in redis.published
        if event["type"] == "tool_called"
    ]
    assert tools == [
        "parse_goal",
        "load_seeded_opportunities",
        "rank_opportunities",
        "generate_action_package",
    ]

    assert fake_supabase._store["fit_scores"]
    assert fake_supabase._store["action_packages"]
