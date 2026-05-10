"""Drive a fixture through a skill, diff vs golden, report.

Usage:
  python -m eval.runner.runner             # runs all fixtures × all skills
  python -m eval.runner.runner --bootstrap  # writes/overwrites goldens

Fixture manifests should have an `eval_inputs` block describing per-skill
input shapes, e.g.:
  "eval_inputs": {
    "parse_goal": {"goal": "...", "company_profile": {...}},
    "score_fit": {"company_profile": {...}, "requirements": [...]},
    ...
  }

When a fixture has no `eval_inputs.<skill>`, the skill is SKIPPED for that
fixture (not failed). This lets us add eval coverage incrementally.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable

from api.llm import LLM
from api.skills.detect_risks.skill import detect_risks
from api.skills.extract_requirements.skill import extract_requirements
from api.skills.generate_action_package.skill import generate_action_package
from api.skills.parse_goal.skill import parse_goal
from api.skills.parse_pdf.skill import parse_pdf
from api.skills.score_fit.skill import score_fit
from eval.runner.differs import diff_within_tolerance

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures"

SKILLS: dict[str, Callable[..., Any]] = {
    "parse_goal": parse_goal,
    "score_fit": score_fit,
    "detect_risks": detect_risks,
    "generate_action_package": generate_action_package,
    "extract_requirements": extract_requirements,
}


async def _run_skill(name: str, inputs: dict[str, Any], fixture_dir: Path, llm: LLM) -> dict[str, Any]:
    skill = SKILLS[name]
    if name == "extract_requirements":
        # Needs parsed PDF; either honor a pre-parsed `parsed` blob in inputs
        # or parse on the fly from a `pdf_path` (relative to fixture dir).
        if "parsed" not in inputs:
            pdf_path = inputs.get("pdf_path")
            if not pdf_path:
                raise ValueError(
                    "extract_requirements eval needs `parsed` or `pdf_path` in inputs"
                )
            parsed = parse_pdf({"path": str(fixture_dir / pdf_path)})
            inputs = {**inputs, "parsed": parsed.model_dump()}
        out, _metrics = await skill(inputs, llm=llm)
    else:
        out, _metrics = await skill(inputs, llm=llm)
    if hasattr(out, "model_dump"):
        return out.model_dump()
    return out  # type: ignore[no-any-return]


async def run_one(
    fixture_dir: Path, skill_name: str, *, bootstrap: bool = False
) -> int:
    """Returns 0 on pass, 1 on fail, 2 on skipped (no inputs declared)."""
    manifest_path = fixture_dir / "manifest.json"
    if not manifest_path.exists():
        return 2
    manifest = json.loads(manifest_path.read_text())
    inputs = manifest.get("eval_inputs", {}).get(skill_name)
    if not inputs:
        print(f"SKIP {skill_name} / {fixture_dir.name} (no eval_inputs declared)")
        return 2
    golden_path = fixture_dir / "goldens" / f"{skill_name}.json"
    llm = LLM()
    out = await _run_skill(skill_name, inputs, fixture_dir, llm)
    if bootstrap or not golden_path.exists():
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
        print(f"BOOTSTRAPPED {skill_name} / {fixture_dir.name}")
        return 0
    expected = json.loads(golden_path.read_text())
    issues = diff_within_tolerance(expected, out)
    if issues:
        print(f"FAIL {skill_name} / {fixture_dir.name}:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print(f"PASS {skill_name} / {fixture_dir.name}")
    return 0


async def main(argv: list[str]) -> int:
    bootstrap = "--bootstrap" in argv
    rc = 0
    if not FIXTURES_DIR.exists():
        print(f"No fixtures dir at {FIXTURES_DIR}", file=sys.stderr)
        return 1
    for fixture in sorted(FIXTURES_DIR.iterdir()):
        if not fixture.is_dir() or fixture.name.startswith("_") or fixture.name.startswith("."):
            continue
        for skill_name in SKILLS:
            sub = await run_one(fixture, skill_name, bootstrap=bootstrap)
            if sub == 1:
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
