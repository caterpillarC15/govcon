# Eval harness

Fixture-driven regression tests for LLM-backed skills.

## What this catches

Drift in skill behavior across model upgrades, prompt edits, or stack
changes. The unit tests under `api/tests/` use `FakeLLM` and verify
shape/contract; these eval runs use a real Anthropic call and verify
*behavior* against committed goldens.

## Cost

Each `make eval` run hits a real LLM for every (fixture × skill) pair
declared in `manifest.json`'s `eval_inputs` block. With 4 fixtures and
5 LLM-backed skills, a full run is up to 20 calls — roughly $0.10–$0.40
per full run depending on model. Run only on PRs that touch
`api/skills/`, `api/llm.py`, fixtures, or migrations.

## Run

```bash
# Bootstrap goldens (overwrites). Run after intentional behavior change.
make eval-bootstrap

# Verify against existing goldens. Use this as the regression gate.
make eval
```

## Adding eval coverage for a fixture

Edit `fixtures/<slug>/manifest.json` and add an `eval_inputs` block:

```json
{
  "slug": "strong-pursue",
  "opportunity": { ... },
  "eval_inputs": {
    "parse_goal": {
      "goal": "Find FedRAMP cyber RFPs in the next 30 days",
      "company_profile": {"naics_codes": ["541512"]}
    },
    "score_fit": {
      "company_profile": { ... },
      "requirements": [ ... ]
    }
  }
}
```

Skills without an entry are skipped for that fixture (not failed).
After adding inputs, run `make eval-bootstrap` once to write the
golden, hand-review the JSON, then `make eval` becomes the regression
gate.

## Tolerance

LLM outputs aren't bit-stable, so `eval/runner/differs.py` applies
per-field rules:

- `total_score` (int): ±5 drift allowed
- `decision` (str): must match exactly
- `evidence_snippet` (str): substring match on first 60 chars
- everything else: structural equality

If a real behavior change makes a golden stale, run `make
eval-bootstrap` and hand-review the diff before committing.
