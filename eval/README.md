# Eval harness

Fixture-driven regression tests for the (now deterministic) GovCon
skills. PRD v1.2.6 made every skill in this repo deterministic;
goldens are byte-exact.

## What this catches

- Accidental shape changes in skill returns (a refactor that drops a
  field, renames a key, changes a default).
- Validator regressions: §11.1 short-circuit logic, §11 evidence-binding
  downgrades, §5.8 risk taxonomy filtering, §5.13 approval-gate
  enforcement, decision-band normalization.
- Anything that changes a fixture's expected output without intent.

It does **not** test the LLM judgment that produces the inputs to
these validators — that's owned by Michaela's bench in
`/root/michealaai`. They have their own eval harness.

## Cost

**Free.** No LLM calls. No `ANTHROPIC_API_KEY` needed.

## Run

```bash
# Bootstrap (or rebuild) goldens after an intentional skill change.
make eval-bootstrap

# Verify against committed goldens. Use as a regression gate on every PR.
make eval
```

## Adding eval coverage for a fixture

Edit `fixtures/<slug>/manifest.json`'s `eval_inputs` block:

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
      "requirements": [ ... ],
      "total_score": 88
    },
    "extract_requirements": {
      "pdf_path": "attachments/main.pdf",
      "requirements": [ ... ]
    }
  }
}
```

Each skill's `eval_inputs.<skill>` is the exact payload the skill is
called with. Re-bootstrap to capture the deterministic output:

```bash
make eval-bootstrap
git add fixtures/<slug>/goldens/
git commit -m "eval(<slug>): bootstrap goldens"
```
