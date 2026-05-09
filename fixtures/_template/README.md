# Fixture Authoring Guide

Each test fixture lives at `fixtures/<slug>/` and represents one real or realistic
federal opportunity with a known expected outcome.

## Directory layout

```
fixtures/<slug>/
  manifest.json          # validated against schemas/fixture-manifest.schema.json
  attachments/
    RFP-001.pdf          # one file per entry in manifest.json "attachments" list
```

## Steps to author a new fixture

1. Copy this directory: `cp -r fixtures/_template fixtures/<your-slug>`
2. Edit `manifest.json` — fill every `TODO` / placeholder value:
   - `slug` must match the directory name and satisfy `^[a-z0-9-]+$`
   - `opportunity.*` must be a valid Opportunity record (all required fields)
   - `attachments` lists the PDFs you will place in `attachments/`
3. Drop real (or redacted) PDF files into `fixtures/<your-slug>/attachments/`.
4. Run `make fixtures-validate` — all manifests under `fixtures/*/` are validated
   against the schema; this directory (`_template`) is skipped automatically.

## Validation

```
make fixtures-validate
```

Output on success:
```
✓ fixtures/my-fixture/manifest.json
Validated 1 fixture(s)
```

Subdirectories whose names begin with `_` (like this template) are skipped by the
validator so you can leave them as reference material without breaking CI.
