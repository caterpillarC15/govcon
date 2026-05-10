# Plans

Active plans live at this directory's root. Once a plan is fully
executed and its outcome is verifiably on `main`, move it to
`_archive/` so future agents reading the plan list see only what's
in flight.

## Active

- `2026-05-10-everything-to-v1.0.0.md` — drift cleanup + launch finish.
  This is the parent plan. When it's done, move it to `_archive/` and
  delete this README's bullet for it.

## Archived

See `_archive/`. Each archived plan is a historical record; do not edit.

- `2026-05-10-finish-it-all.md` — consolidated runway plan; most §5.14 + launch-runway items shipped.
- `2026-05-10-frontend-cleanup-fixes.md` — skeletons, auth hardening, SSE polish, brand alignment.
- `2026-05-10-skills-deterministic-only.md` — PRD v1.2.6 deterministic skill rewrite (api/llm.py removed; eval byte-exact).
