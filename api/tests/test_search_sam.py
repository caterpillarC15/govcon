"""search_sam_opportunities — happy path + degraded fallback paths."""
from __future__ import annotations
import httpx
import respx
from api.skills.search_sam import search_sam_opportunities

SAM_URL = "https://api.sam.gov/opportunities/v2/search"


async def test_happy_path_returns_normalized_opportunities():
    async with respx.mock(base_url="https://api.sam.gov") as router:
        router.get("/opportunities/v2/search").respond(
            200,
            json={
                "opportunitiesData": [
                    {
                        "title": "Cloud Services",
                        "noticeId": "ABC-001",
                        "fullParentPathName": "DOD.AIR FORCE",
                        "naicsCode": "541512",
                        "typeOfSetAsideDescription": "Total Small Business",
                        "responseDeadLine": "2026-06-15T17:00:00",
                        "uiLink": "https://sam.gov/opp/abc",
                        "description": "Cloud migration support.",
                    }
                ]
            },
        )
        out = await search_sam_opportunities(
            {"keywords": "cloud", "naics": "541512"},
            api_key="test-key",
        )
    assert out["degraded"] is False
    assert out["error"] == ""
    assert len(out["opportunities"]) == 1
    opp = out["opportunities"][0]
    assert opp["solicitation_number"] == "ABC-001"
    assert opp["title"] == "Cloud Services"
    assert opp["agency"] == "DOD"
    assert opp["due_date"] == "2026-06-15"
    assert opp["set_aside"] == "Total Small Business"


async def test_429_returns_degraded_with_empty_results():
    async with respx.mock(base_url="https://api.sam.gov") as router:
        router.get("/opportunities/v2/search").respond(429)
        out = await search_sam_opportunities(
            {"keywords": "x"}, api_key="test-key"
        )
    assert out["degraded"] is True
    assert out["opportunities"] == []
    assert "rate limit" in out["error"].lower()


async def test_500_returns_degraded_with_status_in_error():
    async with respx.mock(base_url="https://api.sam.gov") as router:
        router.get("/opportunities/v2/search").respond(503)
        out = await search_sam_opportunities(
            {"keywords": "x"}, api_key="test-key"
        )
    assert out["degraded"] is True
    assert out["opportunities"] == []
    assert "503" in out["error"]


async def test_network_error_returns_degraded():
    async with respx.mock(base_url="https://api.sam.gov") as router:
        router.get("/opportunities/v2/search").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        out = await search_sam_opportunities(
            {"keywords": "x"}, api_key="test-key"
        )
    assert out["degraded"] is True
    assert "network" in out["error"].lower()


async def test_empty_results_not_degraded():
    """SAM returning zero hits is success, not degradation."""
    async with respx.mock(base_url="https://api.sam.gov") as router:
        router.get("/opportunities/v2/search").respond(
            200, json={"opportunitiesData": []}
        )
        out = await search_sam_opportunities(
            {"keywords": "no-hits"}, api_key="test-key"
        )
    assert out["degraded"] is False
    assert out["opportunities"] == []
