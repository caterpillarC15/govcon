# Fixture Template

Each fixture lives at `/fixtures/<slug>/` with:

- `manifest.json` — validated against `schemas/fixture-manifest.schema.json`
- `attachments/<filename>.pdf` — solicitation PDFs (built deterministically by `build_pdf.py`)
- `build_pdf.py` — ReportLab generator; commit it alongside the manifest so PDFs are reproducible

## Workflow

1. Copy this directory: `cp -r fixtures/_template fixtures/<your-slug>`
2. Edit `manifest.json` — set `slug`, `expected_decision_band`, opportunity fields, expected blockers
3. Add a `build_pdf.py` (see existing fixtures for the pattern)
4. Generate the PDF: `uv run python fixtures/<your-slug>/build_pdf.py`
5. Validate: `make fixtures-validate`

The `_template/` directory is **skipped** by the validator and by the
`load_seeded_opportunities` skill — it exists only as a copyable starting point.
