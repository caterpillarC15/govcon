"""load_seeded_opportunities fixture loader tests."""
from __future__ import annotations

import json

from api.skills.load_seeded_opportunities import load_seeded_opportunities

_ALL_FIXTURE_SLUGS = {"strong-pursue", "maybe", "reject", "adversarial-image-pdf"}


async def test_loads_all_four_fixtures(fake_supabase) -> None:
    out = await load_seeded_opportunities({"slugs": None}, client=fake_supabase)
    slugs = {o["slug"] for o in out["opportunities"]}
    assert slugs == _ALL_FIXTURE_SLUGS
    assert len(out["opportunities"]) == 4
    for opp in out["opportunities"]:
        assert "id" in opp
        assert "title" in opp


async def test_loads_specific_subset(fake_supabase) -> None:
    out = await load_seeded_opportunities({"slugs": ["strong-pursue"]}, client=fake_supabase)
    assert len(out["opportunities"]) == 1
    assert out["opportunities"][0]["slug"] == "strong-pursue"


async def test_idempotent_on_repeat(fake_supabase) -> None:
    a = await load_seeded_opportunities({"slugs": ["maybe"]}, client=fake_supabase)
    b = await load_seeded_opportunities({"slugs": ["maybe"]}, client=fake_supabase)
    assert len(a["opportunities"]) == 1
    assert len(b["opportunities"]) == 1
    assert a["opportunities"][0]["id"] == b["opportunities"][0]["id"]


async def test_skips_template_directory(fake_supabase, tmp_path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    template = fixtures_dir / "_template"
    template.mkdir(parents=True)
    (template / "manifest.json").write_text(
        json.dumps({"slug": "should-not-load", "opportunity": {}})
    )

    out = await load_seeded_opportunities(
        {"slugs": None},
        client=fake_supabase,
        fixtures_dir=fixtures_dir,
    )
    assert out["opportunities"] == []
