# GovCapture MVP Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take GovCapture Agent from its current ~40% state (infrastructure + 2 skills) to a shippable MVP that runs the full §13.1 demo: profile + goal → live agent run → ranked opportunities → action package with human approval gate.

**Architecture:** Build out the missing layers in dependency order. Foundation first (POST write paths + /web skeleton + fixtures), then the four analysis skills (score_fit, detect_risks, generate_action_package + helpers), then the Hermes orchestration that ties them together, then the eval harness that pins behavior, then the product UI that consumes the SSE stream, then production hardening.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2.0 async / asyncpg / Alembic / Anthropic SDK / Hermes agent runtime / pypdf / reportlab (test PDFs) / Redis pub-sub / Supabase (PG + Storage) / Next 15 App Router / React 19 / Tailwind 4 / TypeScript / zod / EventSource API.

**Phase Map:**
- **Phase 0** — Pre-flight: POST analysis routes + /web skeleton + fixture template (1 day)
- **Phase 1** — Seeded fixtures: strong-pursue, maybe, reject, adversarial-image (1 day)
- **Phase 2** — Analysis skills: A6 score_fit, A7 detect_risks, A8 generate_action_package (3-4 days)
- **Phase 3** — Discovery + helper skills: A11 search_sam, fetch_attachment, parse_goal, rank, load_seeded (1-2 days)
- **Phase 4** — Hermes integration: A9 runner + bridge + 5 agent personas + A10 human review (3-5 days)
- **Phase 5** — Eval harness A12 (1-2 days)
- **Phase 6** — Product UI in /web (5-7 days, parallel-able after Phase 0)
- **Phase 7** — Production hardening: transactions, retry, logging, budgets (2-3 days)

**Total runway:** ~3 weeks for one engineer; ~2 weeks if Track A (backend) and Track B (frontend) run in parallel after Phase 0.

**Conventions used throughout this plan:**
- Run all tests with `uv run pytest -v` from repo root.
- All commits follow conventional-commit style (`feat:`, `fix:`, `test:`, `chore:`, `docs:`).
- Each task: write failing test → run to confirm fail → implement → run to confirm pass → commit.
- File paths are absolute from repo root `/Volumes/CS_Stuff/govcon/`.

---

# PHASE 0 — Foundation

Unblocks everything else. POST routes give skills a place to write; the /web skeleton gives Track B a home; the fixture template enforces structure for Phase 1.

---

### Task 0.1: Add POST routes for analysis writes

**Why:** Skills (when called by Hermes) need to persist `extracted_requirements`, `fit_scores`, `risk_flags`, `action_packages`. Currently only repositories support inserts; no HTTP path exposes them. Decision: expose via authenticated POST so Hermes-as-subprocess can call them through HTTP (cleanest process boundary; in-process direct repo calls remain available for in-process Hermes if A9 chooses that path).

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/schemas/extracted_requirement_create.py` (Pydantic input model — generate via `make schemas` after schema added, or hand-write thin model)
- Modify: `/Volumes/CS_Stuff/govcon/api/routes/opportunities.py` — add 4 POSTs
- Modify: `/Volumes/CS_Stuff/govcon/api/routes/action_packages.py` — add POST
- Modify: `/Volumes/CS_Stuff/govcon/api/repositories/opportunity.py` — add `create_requirement`, `create_fit_score`, `create_risk_flag` methods
- Modify: `/Volumes/CS_Stuff/govcon/api/repositories/action_package.py` — add `create` method
- Test: `/Volumes/CS_Stuff/govcon/api/tests/test_routes.py` — add 4 POST tests

- [ ] **Step 1: Write failing test for POST /opportunities/{id}/requirements**

Add to `api/tests/test_routes.py`:

```python
@pytest.mark.asyncio
async def test_post_requirement(client: AsyncClient, db_session: AsyncSession) -> None:
    opp = await _seed_opportunity(db_session)
    payload = {
        "type": "eligibility",
        "title": "Small business set-aside",
        "value": "Total small business set-aside",
        "description": "Reserved for small businesses per FAR 19.502-2.",
        "confidence": "high",
        "evidence_snippet": "This requirement is set aside for small businesses.",
        "source_document": "RFP-001.pdf",
        "page_number": 3,
        "is_blocker": False,
    }
    resp = await client.post(f"/opportunities/{opp.id}/requirements", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Small business set-aside"
    assert data["confidence"] == "high"
    assert "id" in data
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest api/tests/test_routes.py::test_post_requirement -v
```
Expected: 405 Method Not Allowed or 404.

- [ ] **Step 3: Add `create_requirement` to opportunity repo**

In `/Volumes/CS_Stuff/govcon/api/repositories/opportunity.py`:

```python
from api.db.models import ExtractedRequirement

async def create_requirement(
    self, opportunity_id: UUID, data: dict
) -> ExtractedRequirement:
    req = ExtractedRequirement(opportunity_id=opportunity_id, **data)
    self._session.add(req)
    await self._session.flush()
    await self._session.commit()
    await self._session.refresh(req)
    return req
```

- [ ] **Step 4: Add POST handler in routes/opportunities.py**

```python
@router.post("/{opportunity_id}/requirements", status_code=201)
async def create_requirement(
    opportunity_id: UUID,
    payload: ExtractedRequirementCreate,
    repo: OpportunityRepo = Depends(get_opportunity_repo),
) -> ExtractedRequirement:
    if not await repo.get(opportunity_id):
        raise HTTPException(404, "Opportunity not found")
    return await repo.create_requirement(opportunity_id, payload.model_dump())
```

- [ ] **Step 5: Run test to verify pass**

```bash
uv run pytest api/tests/test_routes.py::test_post_requirement -v
```
Expected: PASS.

- [ ] **Step 6: Repeat steps 1-5 for fit_scores, risk_flags, action_packages**

Each follows the same pattern. Endpoints:
- `POST /opportunities/{id}/fit-score` → 201, returns FitScore
- `POST /opportunities/{id}/risks` → 201, returns RiskFlag
- `POST /action-packages` (body includes opportunity_id + company_profile_id) → 201

- [ ] **Step 7: Commit**

```bash
git add api/routes/ api/repositories/ api/schemas/ api/tests/test_routes.py
git commit -m "feat(api): POST routes for analysis writes (requirements, fit-score, risks, action-package)"
```

---

### Task 0.2: Create /web Next.js skeleton

**Why:** Track B (product UI) currently has nowhere to live. Landing is marketing only. The product app belongs in `/web/` with its own package.json, separate from `/landing/`.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/web/package.json`
- Create: `/Volumes/CS_Stuff/govcon/web/next.config.mjs`
- Create: `/Volumes/CS_Stuff/govcon/web/tsconfig.json`
- Create: `/Volumes/CS_Stuff/govcon/web/postcss.config.mjs`
- Create: `/Volumes/CS_Stuff/govcon/web/src/app/layout.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/app/page.tsx` (placeholder dashboard)
- Create: `/Volumes/CS_Stuff/govcon/web/src/app/globals.css`
- Modify: `/Volumes/CS_Stuff/govcon/package.json` — add "web" to workspaces array

- [ ] **Step 1: Bootstrap web/ via copy from landing/ as baseline**

```bash
cp /Volumes/CS_Stuff/govcon/landing/package.json /Volumes/CS_Stuff/govcon/web/package.json
cp /Volumes/CS_Stuff/govcon/landing/next.config.mjs /Volumes/CS_Stuff/govcon/web/next.config.mjs
cp /Volumes/CS_Stuff/govcon/landing/tsconfig.json /Volumes/CS_Stuff/govcon/web/tsconfig.json
cp /Volumes/CS_Stuff/govcon/landing/postcss.config.mjs /Volumes/CS_Stuff/govcon/web/postcss.config.mjs
mkdir -p /Volumes/CS_Stuff/govcon/web/src/app /Volumes/CS_Stuff/govcon/web/src/lib /Volumes/CS_Stuff/govcon/web/src/components
```

- [ ] **Step 2: Edit web/package.json — change name + add zod**

Edit `web/package.json`:

```json
{
  "name": "govcapture-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3001",
    "build": "next build",
    "start": "next start -p 3001",
    "lint": "next lint",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "15.5.3",
    "react": "19.2.5",
    "react-dom": "19.2.5",
    "zod": "^3.23.8",
    "lucide-react": "^0.460.0"
  },
  "devDependencies": {
    "@types/node": "^22",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "tailwindcss": "^4.3.0",
    "@tailwindcss/postcss": "^4.3.0",
    "typescript": "~6.0.2"
  }
}
```

- [ ] **Step 3: Add to root workspaces**

Edit `/Volumes/CS_Stuff/govcon/package.json`:

```json
{
  "name": "govcon",
  "private": true,
  "workspaces": ["landing", "web"],
  "scripts": {
    "dev:landing": "npm -w landing run dev --",
    "dev:web": "npm -w web run dev --",
    "build:web": "npm -w web run build",
    "typecheck:web": "npm -w web run typecheck"
  }
}
```

- [ ] **Step 4: Write minimal layout + placeholder page**

`web/src/app/layout.tsx`:

```tsx
import './globals.css';
export const metadata = { title: 'GovCapture' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white text-slate-900 antialiased">{children}</body>
    </html>
  );
}
```

`web/src/app/page.tsx`:

```tsx
export default function Home() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-3xl font-semibold">GovCapture</h1>
      <p className="mt-2 text-slate-600">Product UI scaffold. Routes coming in B3+.</p>
    </main>
  );
}
```

`web/src/app/globals.css`:

```css
@import "tailwindcss";
```

- [ ] **Step 5: Install + smoke test**

```bash
cd /Volumes/CS_Stuff/govcon && npm install
npm -w web run typecheck
npm -w web run dev &
sleep 5 && curl -s http://localhost:3001 | head -5
kill %1
```
Expected: HTML response containing "GovCapture".

- [ ] **Step 6: Commit**

```bash
git add web/ package.json package-lock.json
git commit -m "feat(web): bootstrap product UI Next 15 skeleton at /web"
```

---

### Task 0.3: Create fixture template + manifest schema

**Why:** Phase 1 will author 4 fixtures; they need a consistent structure so `load_seeded_opportunities` can iterate over them, and so `test_parse_pdf` knows where to find PDFs.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/fixtures/_template/manifest.json`
- Create: `/Volumes/CS_Stuff/govcon/fixtures/_template/README.md`
- Create: `/Volumes/CS_Stuff/govcon/schemas/fixture-manifest.schema.json`
- Modify: `/Volumes/CS_Stuff/govcon/Makefile` — add `fixtures-validate` target

- [ ] **Step 1: Write the manifest JSON Schema**

`/Volumes/CS_Stuff/govcon/schemas/fixture-manifest.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "FixtureManifest",
  "description": "Per-fixture metadata used by load_seeded_opportunities and the eval harness.",
  "type": "object",
  "required": ["slug", "expected_decision_band", "opportunity", "attachments"],
  "properties": {
    "slug": { "type": "string", "pattern": "^[a-z0-9-]+$" },
    "expected_decision_band": {
      "type": "string",
      "enum": ["strong_pursue", "pursue", "maybe", "reject"]
    },
    "expected_critical_blockers": { "type": "array", "items": { "type": "string" } },
    "expected_partner_suggestion": { "type": "boolean", "default": false },
    "opportunity": { "$ref": "opportunity.schema.json" },
    "attachments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["filename", "kind"],
        "properties": {
          "filename": { "type": "string" },
          "kind": { "enum": ["solicitation", "amendment", "attachment_other"] }
        }
      }
    }
  }
}
```

- [ ] **Step 2: Write the template manifest + README**

`/Volumes/CS_Stuff/govcon/fixtures/_template/manifest.json`:

```json
{
  "slug": "TEMPLATE-replace-me",
  "expected_decision_band": "strong_pursue",
  "expected_critical_blockers": [],
  "expected_partner_suggestion": false,
  "opportunity": {
    "title": "Replace with real title",
    "agency": "Department of X",
    "solicitation_number": "ABC-1234",
    "source_url": "https://sam.gov/opp/example",
    "due_date": "2026-07-01",
    "naics": "541512",
    "set_aside": "SBA",
    "place_of_performance": "Austin, TX",
    "description": "One-paragraph description.",
    "attachments": ["RFP-001.pdf"],
    "raw_payload": {}
  },
  "attachments": [{ "filename": "RFP-001.pdf", "kind": "solicitation" }]
}
```

`/Volumes/CS_Stuff/govcon/fixtures/_template/README.md`:

```markdown
# Fixture Template

Each fixture lives at `/fixtures/<slug>/` with:
- `manifest.json` — validated against `schemas/fixture-manifest.schema.json`
- `attachments/<filename>.pdf` — real solicitation PDFs

Run `make fixtures-validate` to check all fixtures.
```

- [ ] **Step 3: Add Makefile target**

Append to `Makefile`:

```makefile
fixtures-validate: ## Validate every fixture manifest against the schema
	@uv run python -c "import json, jsonschema, glob; \
	  schema = json.load(open('schemas/fixture-manifest.schema.json')); \
	  resolver = jsonschema.RefResolver(base_uri='file://$(shell pwd)/schemas/', referrer=schema); \
	  [jsonschema.validate(json.load(open(f)), schema, resolver=resolver) or print(f'✓ {f}') \
	   for f in glob.glob('fixtures/*/manifest.json') if not f.startswith('fixtures/_template')]"
```

- [ ] **Step 4: Run validation (no fixtures yet, should pass with no output)**

```bash
make fixtures-validate
```
Expected: empty output (no fixtures yet).

- [ ] **Step 5: Commit**

```bash
git add fixtures/ schemas/fixture-manifest.schema.json Makefile
git commit -m "feat(fixtures): add manifest schema + template + validation target"
```

---

# PHASE 1 — Seeded Fixtures

Four fixtures, each with one realistic SAM-style JSON record + at least one PDF. These unblock 2 skipped tests, the eval harness, the demo, and `load_seeded_opportunities`.

PDFs should be **realistic but clearly fictional** to avoid any confusion with real solicitations. Use ReportLab to generate them programmatically — keeps fixtures version-controllable as code rather than binary blobs that drift.

---

### Task 1.1: Author strong-pursue fixture

**Why:** Highest-fit demo fixture. Should land in 85-100 band. Small business set-aside, NAICS-aligned with the demo company (541512 — Computer Systems Design Services), 30+ days out, clear technical scope, no clearance.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/fixtures/strong-pursue/manifest.json`
- Create: `/Volumes/CS_Stuff/govcon/fixtures/strong-pursue/build_pdf.py` (ReportLab generator)
- Create: `/Volumes/CS_Stuff/govcon/fixtures/strong-pursue/attachments/RFP-001.pdf` (built via above)

- [ ] **Step 1: Write the manifest**

`/Volumes/CS_Stuff/govcon/fixtures/strong-pursue/manifest.json`:

```json
{
  "slug": "strong-pursue",
  "expected_decision_band": "strong_pursue",
  "expected_critical_blockers": [],
  "expected_partner_suggestion": false,
  "opportunity": {
    "title": "Cloud Migration Support Services for the Office of the Chief Information Officer",
    "agency": "Department of the Interior",
    "solicitation_number": "DOI-CMS-2026-001",
    "source_url": "https://sam.gov/opp/example-strong-pursue",
    "due_date": "2026-06-15",
    "naics": "541512",
    "set_aside": "Total Small Business Set-Aside",
    "place_of_performance": "Washington, DC (remote acceptable)",
    "description": "Cloud migration support including assessment, planning, and execution of AWS GovCloud migrations for legacy DOI systems. Period of performance: 12 months base + 2 option years.",
    "attachments": ["RFP-001.pdf"],
    "raw_payload": {}
  },
  "attachments": [{ "filename": "RFP-001.pdf", "kind": "solicitation" }]
}
```

- [ ] **Step 2: Write the PDF builder**

`/Volumes/CS_Stuff/govcon/fixtures/strong-pursue/build_pdf.py`:

```python
"""Build the strong-pursue solicitation PDF. Re-run if content changes."""
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

OUT = Path(__file__).parent / "attachments" / "RFP-001.pdf"

def build() -> None:
    OUT.parent.mkdir(exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("REQUEST FOR PROPOSAL — DOI-CMS-2026-001", styles["Title"]),
        Paragraph("Cloud Migration Support Services", styles["Heading1"]),
        Spacer(1, 12),
        Paragraph("<b>Agency:</b> Department of the Interior", styles["Normal"]),
        Paragraph("<b>Set-Aside:</b> Total Small Business Set-Aside", styles["Normal"]),
        Paragraph("<b>NAICS:</b> 541512 — Computer Systems Design Services", styles["Normal"]),
        Paragraph("<b>Due Date:</b> 15 June 2026, 5:00 PM ET", styles["Normal"]),
        Paragraph("<b>Period of Performance:</b> 12 months base + 2 option years", styles["Normal"]),
        PageBreak(),
        Paragraph("Section L — Submission Instructions", styles["Heading2"]),
        Paragraph(
            "Proposals shall be submitted electronically via SAM.gov no later than 5:00 PM ET "
            "on 15 June 2026. Late submissions will not be considered.", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Section M — Evaluation Criteria", styles["Heading2"]),
        Paragraph(
            "Award will be made to the offeror whose proposal represents the best value to the "
            "Government considering: (1) Technical Approach, (2) Past Performance, (3) Price.",
            styles["Normal"]),
        PageBreak(),
        Paragraph("Section C — Technical Requirements", styles["Heading2"]),
        Paragraph("The contractor shall:", styles["Normal"]),
        Paragraph("1. Conduct cloud-readiness assessments for legacy DOI systems.", styles["Normal"]),
        Paragraph("2. Develop migration roadmaps targeting AWS GovCloud.", styles["Normal"]),
        Paragraph("3. Execute lift-and-shift and refactor migrations.", styles["Normal"]),
        Paragraph("4. Provide post-migration support for 90 days.", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Past Performance Requirement: Minimum 2 federal cloud migration "
                  "engagements completed within the past 5 years.", styles["Normal"]),
    ]
    doc.build(story)
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    build()
```

- [ ] **Step 3: Generate the PDF**

```bash
uv run python /Volumes/CS_Stuff/govcon/fixtures/strong-pursue/build_pdf.py
```
Expected: `Wrote .../attachments/RFP-001.pdf`.

- [ ] **Step 4: Validate manifest**

```bash
make fixtures-validate
```
Expected: `✓ fixtures/strong-pursue/manifest.json`.

- [ ] **Step 5: Run the previously-skipped parse_pdf test**

```bash
uv run pytest api/tests/test_parse_pdf.py -v -k "strong_pursue"
```
Expected: PASS (no longer skipped).

- [ ] **Step 6: Commit**

```bash
git add fixtures/strong-pursue/
git commit -m "feat(fixtures): add strong-pursue fixture (DOI cloud migration RFP)"
```

---

### Task 1.2: Author maybe / needs-partner fixture

**Why:** Should land in 55-69 band, surface a partner suggestion. Past-performance threshold or specialized capability the demo company can't meet alone.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/fixtures/maybe/manifest.json`
- Create: `/Volumes/CS_Stuff/govcon/fixtures/maybe/build_pdf.py`
- Create: `/Volumes/CS_Stuff/govcon/fixtures/maybe/attachments/RFP-002.pdf`

- [ ] **Step 1: Write manifest**

`/Volumes/CS_Stuff/govcon/fixtures/maybe/manifest.json`:

```json
{
  "slug": "maybe",
  "expected_decision_band": "maybe",
  "expected_critical_blockers": [],
  "expected_partner_suggestion": true,
  "opportunity": {
    "title": "Enterprise SIEM Deployment and Managed Detection Services",
    "agency": "Department of Veterans Affairs",
    "solicitation_number": "VA-SIEM-2026-118",
    "source_url": "https://sam.gov/opp/example-maybe",
    "due_date": "2026-07-30",
    "naics": "541512",
    "set_aside": "Total Small Business Set-Aside",
    "place_of_performance": "Multiple VA Medical Centers (CONUS)",
    "description": "Deployment and 24/7 managed operation of enterprise SIEM across 170+ VA medical facilities. Requires demonstrated past performance at scale ($25M+ similar engagements).",
    "attachments": ["RFP-002.pdf"],
    "raw_payload": {}
  },
  "attachments": [{ "filename": "RFP-002.pdf", "kind": "solicitation" }]
}
```

- [ ] **Step 2: Write build_pdf.py**

Pattern matches Task 1.1 step 2. Key content for the PDF body:

```python
# In the body of build():
Paragraph("Section C.4 — Past Performance Requirements", styles["Heading2"]),
Paragraph(
    "Offerors shall demonstrate past performance on a minimum of three (3) federal "
    "engagements of similar size, scope, and complexity within the past 5 years. "
    "Engagements must total no less than $25,000,000 in cumulative value.",
    styles["Normal"]),
Paragraph(
    "24/7/365 SOC operations capability required from contract award. Contractor must "
    "maintain a CONUS-staffed Tier 1/2/3 SOC.",
    styles["Normal"]),
```

- [ ] **Step 3-6:** Same as Task 1.1 (generate, validate, commit).

```bash
uv run python /Volumes/CS_Stuff/govcon/fixtures/maybe/build_pdf.py
make fixtures-validate
git add fixtures/maybe/
git commit -m "feat(fixtures): add maybe fixture (VA SIEM, requires partner)"
```

---

### Task 1.3: Author reject fixture (eligibility blocker)

**Why:** Triggers §11.1 short-circuit. Demands clearance the demo company doesn't hold. Should land 0-54 with `decision=reject`.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/fixtures/reject/manifest.json`
- Create: `/Volumes/CS_Stuff/govcon/fixtures/reject/build_pdf.py`
- Create: `/Volumes/CS_Stuff/govcon/fixtures/reject/attachments/RFP-003.pdf`

- [ ] **Step 1: Write manifest with critical blocker declared**

`/Volumes/CS_Stuff/govcon/fixtures/reject/manifest.json`:

```json
{
  "slug": "reject",
  "expected_decision_band": "reject",
  "expected_critical_blockers": [
    "Requires Top Secret clearance — company has no clearance"
  ],
  "expected_partner_suggestion": false,
  "opportunity": {
    "title": "Classified Network Defense Operations Support",
    "agency": "Department of Defense",
    "solicitation_number": "DOD-CNDO-2026-044",
    "source_url": "https://sam.gov/opp/example-reject",
    "due_date": "2026-08-01",
    "naics": "541512",
    "set_aside": "8(a) Set-Aside",
    "place_of_performance": "Fort Meade, MD (SCIF)",
    "description": "Network defense operations within classified DOD enclaves. Requires cleared personnel and 8(a) certification.",
    "attachments": ["RFP-003.pdf"],
    "raw_payload": {}
  },
  "attachments": [{ "filename": "RFP-003.pdf", "kind": "solicitation" }]
}
```

- [ ] **Step 2: Write build_pdf.py with explicit eligibility language**

Body content critical to include:

```python
Paragraph("Section H — Special Contract Requirements", styles["Heading2"]),
Paragraph(
    "<b>H.1 Security Clearance.</b> All personnel performing under this contract shall "
    "hold an active Top Secret clearance with SCI eligibility at the time of proposal "
    "submission. Clearance sponsorship is NOT available under this contract.",
    styles["Normal"]),
Paragraph(
    "<b>H.2 Set-Aside.</b> This procurement is reserved for SBA-certified 8(a) Business "
    "Development Program participants in good standing.",
    styles["Normal"]),
```

- [ ] **Step 3-6:** Generate, validate, commit per Task 1.1 pattern.

```bash
git commit -m "feat(fixtures): add reject fixture (DOD classified, TS+8a required)"
```

---

### Task 1.4: Author adversarial image-only PDF fixture

**Why:** Exercises the §4.5 unparseable-document recovery path. The PDF is a single page consisting of one rasterized image of text — pypdf cannot extract characters; the skill must mark it `unparseable`.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/fixtures/adversarial-image-pdf/manifest.json`
- Create: `/Volumes/CS_Stuff/govcon/fixtures/adversarial-image-pdf/build_pdf.py`
- Create: `/Volumes/CS_Stuff/govcon/fixtures/adversarial-image-pdf/attachments/RFP-IMAGE.pdf`

- [ ] **Step 1: Manifest declares unparseable expectation**

```json
{
  "slug": "adversarial-image-pdf",
  "expected_decision_band": "reject",
  "expected_critical_blockers": ["Solicitation document unparseable (image-only PDF)"],
  "expected_partner_suggestion": false,
  "opportunity": {
    "title": "Image-Only Scanned Solicitation",
    "agency": "Test Agency",
    "solicitation_number": "TEST-IMG-2026-001",
    "source_url": "https://sam.gov/opp/example-adversarial",
    "due_date": "2026-09-15",
    "naics": "541512",
    "set_aside": "None",
    "place_of_performance": "Unknown",
    "description": "Adversarial fixture: image-only PDF must be marked unparseable.",
    "attachments": ["RFP-IMAGE.pdf"],
    "raw_payload": {}
  },
  "attachments": [{ "filename": "RFP-IMAGE.pdf", "kind": "solicitation" }]
}
```

- [ ] **Step 2: PDF builder draws an image, no text**

`build_pdf.py`:

```python
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics import renderPM
from PIL import Image, ImageDraw, ImageFont
import io

OUT = Path(__file__).parent / "attachments" / "RFP-IMAGE.pdf"

def build() -> None:
    OUT.parent.mkdir(exist_ok=True)
    img = Image.new("RGB", (1700, 2200), white.rgb())
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    except Exception:
        font = ImageFont.load_default()
    d.text((100, 200), "REQUEST FOR PROPOSAL", fill=(0, 0, 0), font=font)
    d.text((100, 400), "Solicitation TEST-IMG-2026-001", fill=(0, 0, 0), font=font)
    d.text((100, 600), "[image of text — should not parse]", fill=(0, 0, 0), font=font)
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_buf.seek(0)
    c = canvas.Canvas(str(OUT), pagesize=LETTER)
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(img_buf), 0, 0, width=LETTER[0], height=LETTER[1])
    c.showPage()
    c.save()
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    build()
```

- [ ] **Step 3: Add Pillow to dev deps**

Edit `pyproject.toml` `[project.optional-dependencies].dev`:

```toml
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "mypy>=1.13",
    "ruff>=0.8",
    "datamodel-code-generator>=0.26",
    "jsonschema>=4.23",
    "reportlab>=4.2",
    "pillow>=10.4",
]
```

```bash
uv sync --all-extras
```

- [ ] **Step 4: Generate the PDF**

```bash
uv run python /Volumes/CS_Stuff/govcon/fixtures/adversarial-image-pdf/build_pdf.py
```

- [ ] **Step 5: Run the previously-skipped parse_pdf adversarial test**

```bash
uv run pytest api/tests/test_parse_pdf.py -v -k "adversarial_image"
```
Expected: PASS — `unparseable: true` returned.

- [ ] **Step 6: Commit**

```bash
git add fixtures/adversarial-image-pdf/ pyproject.toml uv.lock
git commit -m "feat(fixtures): add adversarial image-only PDF fixture"
```

---

### Task 1.5: Implement load_seeded_opportunities skill

**Why:** Hermes Capture Lead needs a tool that loads all four fixtures into the database when SAM is unavailable or `DEMO_USE_SEEDED_ONLY=true`. Also doubles as the eval-harness data loader.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/skills/load_seeded_opportunities/__init__.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/load_seeded_opportunities/skill.py`
- Create: `/Volumes/CS_Stuff/govcon/api/tests/test_load_seeded.py`

- [ ] **Step 1: Write the failing test**

`/Volumes/CS_Stuff/govcon/api/tests/test_load_seeded.py`:

```python
import pytest
from pathlib import Path
from api.skills.load_seeded_opportunities.skill import LoadSeededSkill, LoadSeededInput

@pytest.mark.asyncio
async def test_loads_all_four_fixtures(db_session) -> None:
    repo = OpportunityRepo(db_session)
    skill = LoadSeededSkill(opportunity_repo=repo, fixtures_dir=Path("fixtures"))
    out = await skill.run(LoadSeededInput(slugs=None))
    assert len(out.opportunities) == 4
    slugs = {o.slug for o in out.opportunities}
    assert slugs == {"strong-pursue", "maybe", "reject", "adversarial-image-pdf"}

@pytest.mark.asyncio
async def test_loads_specific_subset(db_session) -> None:
    repo = OpportunityRepo(db_session)
    skill = LoadSeededSkill(opportunity_repo=repo, fixtures_dir=Path("fixtures"))
    out = await skill.run(LoadSeededInput(slugs=["strong-pursue"]))
    assert len(out.opportunities) == 1
    assert out.opportunities[0].slug == "strong-pursue"
```

- [ ] **Step 2: Run to verify fail**

```bash
uv run pytest api/tests/test_load_seeded.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement skill**

`/Volumes/CS_Stuff/govcon/api/skills/load_seeded_opportunities/skill.py`:

```python
"""load_seeded_opportunities — read /fixtures/*/manifest.json, persist to DB."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from api.db.models import Opportunity
from api.repositories.opportunity import OpportunityRepo

@dataclass
class LoadSeededInput:
    slugs: list[str] | None = None  # None = load all

@dataclass
class LoadSeededOutput:
    opportunities: list[Opportunity]

class LoadSeededSkill:
    def __init__(self, opportunity_repo: OpportunityRepo, fixtures_dir: Path) -> None:
        self._repo = opportunity_repo
        self._dir = fixtures_dir

    async def run(self, payload: LoadSeededInput) -> LoadSeededOutput:
        manifests = self._discover_manifests(payload.slugs)
        loaded: list[Opportunity] = []
        for manifest_path in manifests:
            manifest = json.loads(manifest_path.read_text())
            opp_data = dict(manifest["opportunity"])
            opp_data["slug"] = manifest["slug"]
            opp_data["source_notice_id"] = manifest["opportunity"]["solicitation_number"]
            existing = await self._repo.get_by_slug(manifest["slug"])
            if existing:
                loaded.append(existing)
                continue
            opp = await self._repo.create(opp_data)
            loaded.append(opp)
        return LoadSeededOutput(opportunities=loaded)

    def _discover_manifests(self, slugs: list[str] | None) -> Iterable[Path]:
        for fixture_dir in sorted(self._dir.iterdir()):
            if fixture_dir.name.startswith("_") or fixture_dir.name.startswith("."):
                continue
            if not fixture_dir.is_dir():
                continue
            if slugs is not None and fixture_dir.name not in slugs:
                continue
            manifest = fixture_dir / "manifest.json"
            if manifest.exists():
                yield manifest
```

`/Volumes/CS_Stuff/govcon/api/skills/load_seeded_opportunities/__init__.py`:

```python
from api.skills.load_seeded_opportunities.skill import (
    LoadSeededInput, LoadSeededOutput, LoadSeededSkill,
)
__all__ = ["LoadSeededInput", "LoadSeededOutput", "LoadSeededSkill"]
```

- [ ] **Step 4: Add `get_by_slug` and `create` to OpportunityRepo if missing**

Inspect `api/repositories/opportunity.py`. If `get_by_slug` not present, add:

```python
async def get_by_slug(self, slug: str) -> Opportunity | None:
    stmt = select(Opportunity).where(Opportunity.slug == slug)
    return (await self._session.execute(stmt)).scalar_one_or_none()

async def create(self, data: dict) -> Opportunity:
    opp = Opportunity(**data)
    self._session.add(opp)
    await self._session.flush()
    await self._session.commit()
    await self._session.refresh(opp)
    return opp
```

- [ ] **Step 5: Run test to verify pass**

```bash
uv run pytest api/tests/test_load_seeded.py -v
```
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add api/skills/load_seeded_opportunities/ api/repositories/opportunity.py api/tests/test_load_seeded.py
git commit -m "feat(skills): load_seeded_opportunities — read /fixtures into DB"
```

---

# PHASE 2 — Analysis Skills

The three skills that turn parsed solicitations into a decision: score_fit (A6), detect_risks (A7), generate_action_package (A8). All LLM-backed with strict structured output and §11.1 enforcement where it matters most.

---

### Task 2.1: A6 score_fit — write tests with §11.1 short-circuit

**Why:** §11.1 (eligibility conservatism) is the single highest user-harm rule in the product. Test it before implementing. The deterministic short-circuit must trigger before any LLM call when extracted requirements include a hard eligibility blocker.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/tests/test_score_fit.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/score_fit/__init__.py` (stub, will be filled in 2.2)
- Create: `/Volumes/CS_Stuff/govcon/api/skills/score_fit/skill.py` (stub)

- [ ] **Step 1: Write the failing tests (5 cases)**

`/Volumes/CS_Stuff/govcon/api/tests/test_score_fit.py`:

```python
"""score_fit — §5.7 rubric + §11.1 deterministic short-circuit."""
import pytest
from api.skills.score_fit.skill import (
    ScoreFitSkill, ScoreFitInput, ScoreFitOutput,
)
from api.tests.fakes import FakeLLM  # reuse from test_extract_requirements

@pytest.fixture
def cleared_company() -> dict:
    return {
        "name": "DemoCo", "naics_codes": ["541512"],
        "certifications": ["CMMC L2"], "small_business_status": True,
        "clearance_status": "none",
        "capabilities": ["cloud migration", "AWS GovCloud"],
    }

@pytest.fixture
def uncleared_company() -> dict:
    return {
        "name": "DemoCo", "naics_codes": ["541512"],
        "certifications": [], "small_business_status": True,
        "clearance_status": "none",
        "capabilities": ["network defense"],
    }

# §11.1 — hard short-circuit, no LLM call
@pytest.mark.asyncio
async def test_clearance_required_company_has_none_short_circuits(uncleared_company):
    requirements = [
        {"type": "security", "title": "TS clearance required",
         "value": "Top Secret + SCI", "confidence": "high",
         "is_blocker": True, "evidence_snippet": "TS/SCI required",
         "source_document": "RFP-003.pdf", "page_number": 3, "description": "..."},
    ]
    fake_llm = FakeLLM(should_not_be_called=True)
    skill = ScoreFitSkill(llm=fake_llm)
    out = await skill.run(ScoreFitInput(
        company_profile=uncleared_company, requirements=requirements
    ))
    assert out.decision == "reject"
    assert out.total_score == 0
    assert out.score_breakdown["eligibility"] == 0
    assert any("clearance" in b.lower() for b in out.blockers)
    assert fake_llm.call_count == 0

@pytest.mark.asyncio
async def test_set_aside_mismatch_short_circuits(cleared_company):
    requirements = [
        {"type": "eligibility", "title": "8(a) set-aside",
         "value": "8(a) participants only", "confidence": "high",
         "is_blocker": True, "evidence_snippet": "8(a) set-aside",
         "source_document": "RFP-003.pdf", "page_number": 1, "description": "..."},
    ]
    fake_llm = FakeLLM(should_not_be_called=True)
    skill = ScoreFitSkill(llm=fake_llm)
    out = await skill.run(ScoreFitInput(
        company_profile={**cleared_company, "certifications": ["CMMC L2"]},
        requirements=requirements,
    ))
    assert out.decision == "reject"
    assert out.total_score == 0
    assert fake_llm.call_count == 0

@pytest.mark.asyncio
async def test_eligibility_uncertain_treated_as_blocker(cleared_company):
    """§11.1: 'If eligibility is uncertain, score 0 and emit critical blocker.'"""
    requirements = [
        {"type": "eligibility", "title": "Foreign ownership unclear",
         "value": "May require US-owned entity", "confidence": "low",
         "is_blocker": False, "evidence_snippet": "...",
         "source_document": "RFP.pdf", "page_number": 2, "description": "..."},
    ]
    fake_llm = FakeLLM(should_not_be_called=True)
    skill = ScoreFitSkill(llm=fake_llm)
    out = await skill.run(ScoreFitInput(
        company_profile=cleared_company, requirements=requirements
    ))
    assert out.decision == "reject"
    assert out.score_breakdown["eligibility"] == 0
    assert fake_llm.call_count == 0

# Non-blocker path — LLM is called, full rubric scored
@pytest.mark.asyncio
async def test_no_eligibility_blockers_calls_llm(cleared_company):
    requirements = [
        {"type": "technical", "title": "Cloud migration experience",
         "value": "AWS GovCloud preferred", "confidence": "high",
         "is_blocker": False, "evidence_snippet": "AWS GovCloud preferred",
         "source_document": "RFP-001.pdf", "page_number": 3, "description": "..."},
        {"type": "deadline", "title": "Due 2026-06-15",
         "value": "2026-06-15", "confidence": "high", "is_blocker": False,
         "evidence_snippet": "due 2026-06-15", "source_document": "RFP-001.pdf",
         "page_number": 1, "description": "..."},
    ]
    fake_llm = FakeLLM(canned_response={
        "total_score": 88, "decision": "strong_pursue", "confidence": "high",
        "score_breakdown": {"capability": 18, "eligibility": 14, "naics": 9,
            "past_performance": 12, "certification": 9, "insurance_bonding": 8,
            "deadline": 10, "complexity": 4, "geography": 4},
        "strengths": ["Strong AWS GovCloud experience"],
        "weaknesses": [], "blockers": [], "missing_information": [],
        "recommended_next_action": "Begin proposal drafting.",
    })
    skill = ScoreFitSkill(llm=fake_llm)
    out = await skill.run(ScoreFitInput(
        company_profile=cleared_company, requirements=requirements
    ))
    assert out.decision == "strong_pursue"
    assert out.total_score == 88
    assert fake_llm.call_count == 1

@pytest.mark.asyncio
async def test_decision_band_normalized_to_total(cleared_company):
    """Even if LLM returns inconsistent decision/score, decision_band rule wins."""
    requirements = [{"type": "technical", "title": "X", "value": "X",
        "confidence": "high", "is_blocker": False, "evidence_snippet": "x",
        "source_document": "x.pdf", "page_number": 1, "description": "..."}]
    fake_llm = FakeLLM(canned_response={
        "total_score": 60, "decision": "strong_pursue",  # inconsistent
        "confidence": "high",
        "score_breakdown": {"capability": 12, "eligibility": 10, "naics": 6,
            "past_performance": 8, "certification": 6, "insurance_bonding": 6,
            "deadline": 6, "complexity": 3, "geography": 3},
        "strengths": [], "weaknesses": [], "blockers": [],
        "missing_information": [], "recommended_next_action": "...",
    })
    skill = ScoreFitSkill(llm=fake_llm)
    out = await skill.run(ScoreFitInput(
        company_profile=cleared_company, requirements=requirements
    ))
    assert out.decision == "maybe"  # normalized from total_score=60
```

- [ ] **Step 2: Add a `should_not_be_called` knob to FakeLLM**

If not present, extend `api/tests/fakes.py` (create if missing — relocate FakeLLM from `test_extract_requirements.py` so it can be reused):

```python
"""Shared test doubles."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from api.llm import LLMMetrics

class FakeLLM:
    def __init__(
        self,
        canned_response: dict | None = None,
        should_not_be_called: bool = False,
    ) -> None:
        self._canned = canned_response
        self._should_not_be_called = should_not_be_called
        self.call_count = 0

    async def generate_structured(self, **kwargs: Any) -> tuple[dict, LLMMetrics]:
        if self._should_not_be_called:
            raise AssertionError("LLM should not have been called (§11.1 short-circuit)")
        self.call_count += 1
        return (
            self._canned or {},
            LLMMetrics(model="fake", latency_ms=0, cost_usd=0.0,
                       input_tokens=0, output_tokens=0,
                       cache_read_tokens=0, cache_creation_tokens=0, attempts=1),
        )
```

- [ ] **Step 3: Run tests to verify fail**

```bash
uv run pytest api/tests/test_score_fit.py -v
```
Expected: ImportError (skill not implemented).

- [ ] **Step 4: Commit tests**

```bash
git add api/tests/test_score_fit.py api/tests/fakes.py
git commit -m "test(score_fit): §11.1 short-circuit + rubric + decision band tests"
```

---

### Task 2.2: A6 score_fit — implement skill

**Why:** Implement against the test suite from 2.1. The §11.1 short-circuit is a deterministic Python check before any LLM call — never trust the model with this rule.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/skills/score_fit/skill.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/score_fit/__init__.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/score_fit/prompt.txt`

- [ ] **Step 1: Write the prompt**

`/Volumes/CS_Stuff/govcon/api/skills/score_fit/prompt.txt`:

```
You are the Compliance Officer in a govcon bid-desk system. You score how well a small business
fits a federal opportunity using the §5.7 rubric below. You produce JSON only — no prose.

§5.7 rubric (sum to 100):
- capability_match: 20
- eligibility_match: 15  ← already pre-checked deterministically; NEVER override below
- naics_match: 10
- past_performance_fit: 15
- certification_readiness: 10
- insurance_bonding_readiness: 10
- deadline_feasibility: 10
- proposal_complexity: 5
- geography_fit: 5

DECISION BANDS (set decision strictly from total_score):
- 85-100: strong_pursue
- 70-84:  pursue
- 55-69:  maybe
-  0-54:  reject

Behavior rules:
- Be conservative. If a dimension is uncertain, score it lower.
- Do NOT invent capabilities or certifications the company hasn't declared.
- For weaknesses, name the specific gap, not vague platitudes.
- For recommended_next_action: one sentence, imperative voice, what the team does NEXT.
```

- [ ] **Step 2: Implement skill**

`/Volumes/CS_Stuff/govcon/api/skills/score_fit/skill.py`:

```python
"""score_fit — §5.7 rubric + §11.1 deterministic short-circuit (pre-LLM)."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from api.llm import LLMClient, LLMMetrics

PROMPT = (Path(__file__).parent / "prompt.txt").read_text()

ELIGIBILITY_BLOCKER_TYPES = {"eligibility", "security", "certification"}
SET_ASIDE_KEYWORDS = ("8(a)", "hubzone", "wosb", "edwosb", "sdvosb", "vosb")
CLEARANCE_KEYWORDS = ("secret", "ts/sci", "top secret", "clearance")


@dataclass
class ScoreFitInput:
    company_profile: dict
    requirements: list[dict]


@dataclass
class ScoreFitOutput:
    total_score: int
    decision: Literal["strong_pursue", "pursue", "maybe", "reject"]
    confidence: Literal["high", "medium", "low"]
    score_breakdown: dict[str, int]
    strengths: list[str]
    weaknesses: list[str]
    blockers: list[str]
    missing_information: list[str]
    recommended_next_action: str
    metrics: LLMMetrics


def _band_from_score(score: int) -> str:
    if score >= 85:
        return "strong_pursue"
    if score >= 70:
        return "pursue"
    if score >= 55:
        return "maybe"
    return "reject"


def _check_eligibility_short_circuit(profile: dict, requirements: list[dict]) -> list[str] | None:
    """Return list of blockers if §11.1 trips, else None."""
    blockers: list[str] = []
    company_certs = {c.lower() for c in profile.get("certifications", [])}
    company_clearance = (profile.get("clearance_status") or "none").lower()

    for req in requirements:
        if req.get("type") not in ELIGIBILITY_BLOCKER_TYPES:
            continue
        text = f"{req.get('title','')} {req.get('value','')} {req.get('description','')}".lower()
        # Set-aside mismatch
        for keyword in SET_ASIDE_KEYWORDS:
            if keyword in text:
                if not any(keyword in c for c in company_certs):
                    blockers.append(
                        f"Set-aside requires {keyword.upper()}; company is not certified."
                    )
        # Clearance mismatch
        for kw in CLEARANCE_KEYWORDS:
            if kw in text and company_clearance == "none":
                blockers.append(
                    f"Clearance required ({req.get('title','')}) — company has none."
                )
                break
        # Low confidence on eligibility = treat as blocker
        if req.get("type") == "eligibility" and req.get("confidence") in {"low", "unknown"}:
            blockers.append(
                f"Eligibility uncertain: {req.get('title','')} (low/unknown confidence)."
            )
        # is_blocker flag set explicitly
        if req.get("is_blocker") and req.get("type") in ELIGIBILITY_BLOCKER_TYPES:
            blockers.append(req.get("title", "Unnamed eligibility blocker"))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique = [b for b in blockers if not (b in seen or seen.add(b))]
    return unique or None


class ScoreFitSkill:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def run(self, payload: ScoreFitInput) -> ScoreFitOutput:
        # §11.1 deterministic short-circuit BEFORE any LLM call
        blockers = _check_eligibility_short_circuit(
            payload.company_profile, payload.requirements
        )
        if blockers:
            return ScoreFitOutput(
                total_score=0,
                decision="reject",
                confidence="high",
                score_breakdown={
                    "capability": 0, "eligibility": 0, "naics": 0,
                    "past_performance": 0, "certification": 0,
                    "insurance_bonding": 0, "deadline": 0,
                    "complexity": 0, "geography": 0,
                },
                strengths=[],
                weaknesses=[],
                blockers=blockers,
                missing_information=[],
                recommended_next_action="Do not pursue. Critical eligibility blocker(s) present.",
                metrics=LLMMetrics(
                    model="none", latency_ms=0, cost_usd=0.0,
                    input_tokens=0, output_tokens=0,
                    cache_read_tokens=0, cache_creation_tokens=0, attempts=0,
                ),
            )

        # No short-circuit — call LLM with rubric
        result, metrics = await self._llm.generate_structured(
            system=PROMPT,
            user=self._build_user_prompt(payload),
            schema=self._output_schema(),
        )
        # Normalize decision to band rule (LLM may disagree)
        result["decision"] = _band_from_score(result["total_score"])
        return ScoreFitOutput(**result, metrics=metrics)

    def _build_user_prompt(self, payload: ScoreFitInput) -> str:
        import json
        return (
            "Company profile:\n" + json.dumps(payload.company_profile, indent=2) +
            "\n\nExtracted requirements:\n" + json.dumps(payload.requirements, indent=2) +
            "\n\nReturn JSON per the schema."
        )

    def _output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["total_score", "decision", "confidence", "score_breakdown",
                         "strengths", "weaknesses", "blockers", "missing_information",
                         "recommended_next_action"],
            "properties": {
                "total_score": {"type": "integer", "minimum": 0, "maximum": 100},
                "decision": {"enum": ["strong_pursue", "pursue", "maybe", "reject"]},
                "confidence": {"enum": ["high", "medium", "low"]},
                "score_breakdown": {"type": "object"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "weaknesses": {"type": "array", "items": {"type": "string"}},
                "blockers": {"type": "array", "items": {"type": "string"}},
                "missing_information": {"type": "array", "items": {"type": "string"}},
                "recommended_next_action": {"type": "string"},
            },
        }
```

- [ ] **Step 3: Add `__init__.py`**

```python
from api.skills.score_fit.skill import ScoreFitSkill, ScoreFitInput, ScoreFitOutput
__all__ = ["ScoreFitSkill", "ScoreFitInput", "ScoreFitOutput"]
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest api/tests/test_score_fit.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add api/skills/score_fit/
git commit -m "feat(skills): A6 score_fit with §11.1 deterministic short-circuit"
```

---

### Task 2.3: A7 detect_risks — write tests

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/tests/test_detect_risks.py`

**Risk categories per §5.8:** clearance_required, set_aside_mismatch, certification_gap, past_performance_weakness, deadline_too_close, missing_attachments, submission_ambiguity, insurance_bonding_gap, scope_mismatch, legal_compliance_review, pricing_complexity, missing_required_document.
**Severities:** critical_blocker, major_risk, moderate_risk, minor_concern.

- [ ] **Step 1: Write tests covering taxonomy enforcement, evidence binding, severity escalation**

```python
"""detect_risks — §5.8 risk taxonomy + severity calibration."""
import pytest
from api.skills.detect_risks.skill import DetectRisksSkill, DetectRisksInput
from api.tests.fakes import FakeLLM

@pytest.mark.asyncio
async def test_deadline_too_close_calibrated_as_major():
    requirements = [
        {"type": "deadline", "title": "Due in 5 days",
         "value": "2026-05-14", "confidence": "high", "is_blocker": False,
         "evidence_snippet": "Due 2026-05-14", "source_document": "RFP.pdf",
         "page_number": 1, "description": "..."}
    ]
    fake_llm = FakeLLM(canned_response={
        "risks": [{
            "category": "deadline_too_close",
            "severity": "major_risk",
            "title": "Deadline 5 days out",
            "description": "Insufficient runway for full proposal cycle.",
            "evidence": "Due 2026-05-14",
            "mitigation": "Decline or compress technical-volume drafting.",
            "requires_human_review": True,
        }]
    })
    skill = DetectRisksSkill(llm=fake_llm)
    out = await skill.run(DetectRisksInput(
        company_profile={"name": "X"},
        requirements=requirements,
        opportunity={"due_date": "2026-05-14"},
    ))
    assert len(out.risks) == 1
    assert out.risks[0].category == "deadline_too_close"
    assert out.risks[0].severity == "major_risk"

@pytest.mark.asyncio
async def test_invalid_category_filtered_out():
    fake_llm = FakeLLM(canned_response={
        "risks": [{
            "category": "made_up_category",  # not in taxonomy
            "severity": "minor_concern", "title": "X", "description": "Y",
            "evidence": "Z", "mitigation": "W", "requires_human_review": False,
        }]
    })
    skill = DetectRisksSkill(llm=fake_llm)
    out = await skill.run(DetectRisksInput(
        company_profile={}, requirements=[], opportunity={}
    ))
    assert len(out.risks) == 0  # filtered

@pytest.mark.asyncio
async def test_critical_severity_marks_human_review():
    """Any critical_blocker MUST set requires_human_review=True even if LLM forgot."""
    fake_llm = FakeLLM(canned_response={
        "risks": [{
            "category": "set_aside_mismatch",
            "severity": "critical_blocker",
            "title": "8(a) required, company not certified",
            "description": "...", "evidence": "8(a) set-aside",
            "mitigation": "...",
            "requires_human_review": False,  # LLM forgot
        }]
    })
    skill = DetectRisksSkill(llm=fake_llm)
    out = await skill.run(DetectRisksInput(
        company_profile={}, requirements=[], opportunity={}
    ))
    assert out.risks[0].requires_human_review is True  # forced
```

- [ ] **Step 2-3: Run to fail, commit tests**

```bash
uv run pytest api/tests/test_detect_risks.py -v  # fails
git add api/tests/test_detect_risks.py
git commit -m "test(detect_risks): taxonomy + severity + human-review enforcement"
```

---

### Task 2.4: A7 detect_risks — implement

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/skills/detect_risks/skill.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/detect_risks/__init__.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/detect_risks/prompt.txt`

- [ ] **Step 1: Write prompt**

```
You are the Risk Analyst. You inspect extracted requirements and flag risks per §5.8.

Allowed categories ONLY:
clearance_required, set_aside_mismatch, certification_gap, past_performance_weakness,
deadline_too_close, missing_attachments, submission_ambiguity, insurance_bonding_gap,
scope_mismatch, legal_compliance_review, pricing_complexity, missing_required_document

Severities: critical_blocker | major_risk | moderate_risk | minor_concern

For each risk:
- title: short, specific
- description: 1-2 sentences explaining the risk
- evidence: verbatim quote from a requirement (or "no source" if inferred)
- mitigation: what the company can do — concrete, not "review carefully"
- requires_human_review: true for critical_blocker and any legal/compliance-flagged risk

Return JSON only.
```

- [ ] **Step 2: Implement**

```python
"""detect_risks — §5.8 taxonomy + severity calibration + human-review forcing."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from api.llm import LLMClient, LLMMetrics

PROMPT = (Path(__file__).parent / "prompt.txt").read_text()

ALLOWED_CATEGORIES = frozenset({
    "clearance_required", "set_aside_mismatch", "certification_gap",
    "past_performance_weakness", "deadline_too_close", "missing_attachments",
    "submission_ambiguity", "insurance_bonding_gap", "scope_mismatch",
    "legal_compliance_review", "pricing_complexity", "missing_required_document",
})

@dataclass
class RiskFlag:
    category: str
    severity: Literal["critical_blocker", "major_risk", "moderate_risk", "minor_concern"]
    title: str
    description: str
    evidence: str
    mitigation: str
    requires_human_review: bool

@dataclass
class DetectRisksInput:
    company_profile: dict
    requirements: list[dict]
    opportunity: dict

@dataclass
class DetectRisksOutput:
    risks: list[RiskFlag]
    metrics: LLMMetrics

class DetectRisksSkill:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def run(self, payload: DetectRisksInput) -> DetectRisksOutput:
        result, metrics = await self._llm.generate_structured(
            system=PROMPT,
            user=self._build_user(payload),
            schema=self._schema(),
        )
        risks: list[RiskFlag] = []
        for r in result.get("risks", []):
            if r.get("category") not in ALLOWED_CATEGORIES:
                continue  # silently drop unknown taxonomy
            # Force human review on critical / legal flags
            if r.get("severity") == "critical_blocker" or \
               r.get("category") == "legal_compliance_review":
                r["requires_human_review"] = True
            risks.append(RiskFlag(**r))
        return DetectRisksOutput(risks=risks, metrics=metrics)

    def _build_user(self, payload: DetectRisksInput) -> str:
        import json
        return (
            "Company profile:\n" + json.dumps(payload.company_profile, indent=2) +
            "\n\nOpportunity:\n" + json.dumps(payload.opportunity, indent=2) +
            "\n\nRequirements:\n" + json.dumps(payload.requirements, indent=2) +
            "\n\nReturn JSON per schema."
        )

    def _schema(self) -> dict:
        return {
            "type": "object",
            "required": ["risks"],
            "properties": {
                "risks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["category", "severity", "title", "description",
                                     "evidence", "mitigation", "requires_human_review"],
                        "properties": {
                            "category": {"type": "string"},
                            "severity": {"enum": [
                                "critical_blocker", "major_risk",
                                "moderate_risk", "minor_concern"]},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "evidence": {"type": "string"},
                            "mitigation": {"type": "string"},
                            "requires_human_review": {"type": "boolean"},
                        },
                    },
                }
            },
        }
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest api/tests/test_detect_risks.py -v
```
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add api/skills/detect_risks/
git commit -m "feat(skills): A7 detect_risks with §5.8 taxonomy filtering"
```

---

### Task 2.5: A8 generate_action_package — tests for both modes

**Why:** Per AGENT_ARCHITECTURE.md, this skill has two modes:
- `mode=full` — LLM generates §5.11 sections (executive brief, compliance matrix, risk register, proposal checklist, timeline, partner suggestion, outreach draft, approval gate).
- `mode=reject_summary` — Deterministic, no LLM. Slim package: blockers + "do not pursue" recommendation + approval gate. Used by Capture Analyst when Compliance Officer returns reject.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/tests/test_generate_action_package.py`

- [ ] **Step 1: Write tests for both modes**

```python
"""generate_action_package — full mode (LLM) + reject_summary mode (deterministic)."""
import pytest
from api.skills.generate_action_package.skill import (
    GenerateActionPackageSkill, GenerateActionPackageInput,
)
from api.tests.fakes import FakeLLM

@pytest.mark.asyncio
async def test_reject_summary_mode_does_not_call_llm():
    fake_llm = FakeLLM(should_not_be_called=True)
    skill = GenerateActionPackageSkill(llm=fake_llm)
    out = await skill.run(GenerateActionPackageInput(
        mode="reject_summary",
        company_profile={"name": "DemoCo"},
        opportunity={"title": "Classified Net Defense"},
        requirements=[],
        fit_score={"total_score": 0, "decision": "reject", "blockers": [
            "TS clearance required — company has none"]},
        risks=[],
    ))
    assert out.decision == "reject"
    assert "Do not pursue" in out.executive_summary
    assert len(out.compliance_matrix) == 0
    assert len(out.proposal_checklist) == 0
    assert len(out.timeline) == 0
    assert out.outreach_draft is None
    assert "Critical eligibility" in " ".join(out.human_approval_required)
    assert fake_llm.call_count == 0

@pytest.mark.asyncio
async def test_full_mode_calls_llm_and_includes_all_sections():
    fake_llm = FakeLLM(canned_response={
        "executive_summary": "Strong fit. Proceed.",
        "decision": "strong_pursue",
        "fit_score": 88,
        "fit_rationale": "...",
        "compliance_matrix": [{"requirement": "X", "status": "met",
            "evidence": "Y", "next_action": "Z", "owner": "Capture"}],
        "risk_register": [{"risk": "X", "severity": "minor", "explanation": "Y",
            "mitigation": "Z"}],
        "proposal_checklist": ["Verify SAM"],
        "timeline": [{"date": "2026-06-01", "task": "Kickoff", "owner": "PM"}],
        "partner_suggestions": [],
        "outreach_draft": {"subject": "Re: DOI-CMS-2026-001",
            "body": "Hello..."},
        "human_approval_required": ["Approve outreach before sending."],
    })
    skill = GenerateActionPackageSkill(llm=fake_llm)
    out = await skill.run(GenerateActionPackageInput(
        mode="full",
        company_profile={"name": "DemoCo"},
        opportunity={"title": "DOI Cloud"},
        requirements=[{"title": "X", "type": "technical", "confidence": "high",
            "value": "X", "evidence_snippet": "X", "is_blocker": False,
            "source_document": "X", "page_number": 1, "description": "..."}],
        fit_score={"total_score": 88, "decision": "strong_pursue", "blockers": []},
        risks=[],
    ))
    assert out.decision == "strong_pursue"
    assert len(out.compliance_matrix) == 1
    assert len(out.proposal_checklist) == 1
    assert out.outreach_draft is not None
    assert fake_llm.call_count == 1

@pytest.mark.asyncio
async def test_human_approval_block_always_present():
    """§5.13: action package MUST include human approval block."""
    fake_llm = FakeLLM(canned_response={
        "executive_summary": "X", "decision": "pursue", "fit_score": 75,
        "fit_rationale": "X", "compliance_matrix": [], "risk_register": [],
        "proposal_checklist": [], "timeline": [], "partner_suggestions": [],
        "outreach_draft": None,
        "human_approval_required": [],  # LLM forgot!
    })
    skill = GenerateActionPackageSkill(llm=fake_llm)
    out = await skill.run(GenerateActionPackageInput(
        mode="full", company_profile={}, opportunity={"title": "X"},
        requirements=[], fit_score={"total_score": 75, "decision": "pursue",
            "blockers": []}, risks=[],
    ))
    assert len(out.human_approval_required) > 0  # forced default added
```

- [ ] **Step 2: Run, fail, commit tests**

```bash
uv run pytest api/tests/test_generate_action_package.py -v
git add api/tests/test_generate_action_package.py
git commit -m "test(generate_action_package): full + reject_summary mode tests"
```

---

### Task 2.6: A8 generate_action_package — implement

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/skills/generate_action_package/skill.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/generate_action_package/__init__.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/generate_action_package/prompt.txt`

- [ ] **Step 1: Write prompt for full mode**

```
You are the Proposal Strategist. You produce the action package per §5.11 — executive
brief, compliance matrix, risk register, proposal checklist, timeline, partner
suggestion, outreach draft, human approval block.

Rules:
- Decision and fit_score are GIVEN — do not re-derive.
- Compliance matrix: one row per requirement. status ∈ {met, missing, unclear, not_applicable}.
- Proposal checklist: concrete next actions, imperative voice, with owner.
- Timeline: dates work backward from due_date, owner per task.
- Partner suggestion: only if there's a real gap. Never invent contact info.
- Outreach draft: short, professional, no claims of compliance, ends with internal CTA.
- human_approval_required: ALWAYS include at least one item — minimum:
  "Authorized review required before any external action (outreach, submission)."

Return JSON only.
```

- [ ] **Step 2: Implement skill**

```python
"""generate_action_package — full (LLM) + reject_summary (deterministic) modes."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from api.llm import LLMClient, LLMMetrics

PROMPT = (Path(__file__).parent / "prompt.txt").read_text()

DEFAULT_APPROVAL = (
    "Authorized review required before any external action "
    "(outreach, submission, claims of compliance)."
)

@dataclass
class GenerateActionPackageInput:
    mode: Literal["full", "reject_summary"]
    company_profile: dict
    opportunity: dict
    requirements: list[dict]
    fit_score: dict
    risks: list[dict]

@dataclass
class ActionPackageOutput:
    executive_summary: str
    decision: str
    fit_score: int
    fit_rationale: str
    compliance_matrix: list[dict]
    risk_register: list[dict]
    proposal_checklist: list[str]
    timeline: list[dict]
    partner_suggestions: list[dict]
    outreach_draft: dict | None
    human_approval_required: list[str]
    metrics: LLMMetrics

class GenerateActionPackageSkill:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def run(self, payload: GenerateActionPackageInput) -> ActionPackageOutput:
        if payload.mode == "reject_summary":
            return self._reject_summary(payload)
        return await self._full(payload)

    def _reject_summary(self, p: GenerateActionPackageInput) -> ActionPackageOutput:
        blockers = p.fit_score.get("blockers", [])
        opp_title = p.opportunity.get("title", "this opportunity")
        return ActionPackageOutput(
            executive_summary=(
                f"Do not pursue {opp_title}. "
                f"Critical eligibility blocker(s): {'; '.join(blockers) or 'see fit score'}."
            ),
            decision="reject",
            fit_score=p.fit_score.get("total_score", 0),
            fit_rationale=f"Eligibility short-circuit (§11.1). Blockers: {blockers}",
            compliance_matrix=[],
            risk_register=[
                {"risk": b, "severity": "critical", "explanation": "",
                 "mitigation": "Out of scope — pursue only if certification/clearance acquired."}
                for b in blockers
            ],
            proposal_checklist=[],
            timeline=[],
            partner_suggestions=[],
            outreach_draft=None,
            human_approval_required=[
                f"Critical eligibility blocker(s) detected for {opp_title}. {DEFAULT_APPROVAL}"
            ],
            metrics=LLMMetrics(model="none", latency_ms=0, cost_usd=0.0,
                input_tokens=0, output_tokens=0,
                cache_read_tokens=0, cache_creation_tokens=0, attempts=0),
        )

    async def _full(self, p: GenerateActionPackageInput) -> ActionPackageOutput:
        import json
        result, metrics = await self._llm.generate_structured(
            system=PROMPT,
            user=(
                f"Opportunity:\n{json.dumps(p.opportunity, indent=2)}\n\n"
                f"Company profile:\n{json.dumps(p.company_profile, indent=2)}\n\n"
                f"Requirements:\n{json.dumps(p.requirements, indent=2)}\n\n"
                f"Fit score:\n{json.dumps(p.fit_score, indent=2)}\n\n"
                f"Risks:\n{json.dumps(p.risks, indent=2)}\n\nReturn JSON."
            ),
            schema=self._schema(),
        )
        # Force default approval if LLM omitted
        if not result.get("human_approval_required"):
            result["human_approval_required"] = [DEFAULT_APPROVAL]
        return ActionPackageOutput(**result, metrics=metrics)

    def _schema(self) -> dict:
        return {
            "type": "object",
            "required": ["executive_summary", "decision", "fit_score", "fit_rationale",
                "compliance_matrix", "risk_register", "proposal_checklist", "timeline",
                "partner_suggestions", "human_approval_required"],
            "properties": {
                "executive_summary": {"type": "string"},
                "decision": {"type": "string"},
                "fit_score": {"type": "integer"},
                "fit_rationale": {"type": "string"},
                "compliance_matrix": {"type": "array"},
                "risk_register": {"type": "array"},
                "proposal_checklist": {"type": "array", "items": {"type": "string"}},
                "timeline": {"type": "array"},
                "partner_suggestions": {"type": "array"},
                "outreach_draft": {"type": ["object", "null"]},
                "human_approval_required": {"type": "array", "items": {"type": "string"}},
            },
        }
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest api/tests/test_generate_action_package.py -v
```
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add api/skills/generate_action_package/
git commit -m "feat(skills): A8 generate_action_package — full + reject_summary modes"
```

---

# PHASE 3 — Discovery + Helper Skills

`search_sam_opportunities`, `fetch_attachment`, `parse_goal`, `rank_opportunities`. None LLM-heavy except parse_goal; mostly plumbing.

---

### Task 3.1: A11 search_sam_opportunities

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/skills/search_sam/skill.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/search_sam/__init__.py`
- Create: `/Volumes/CS_Stuff/govcon/api/tests/test_search_sam.py`

**Endpoint:** SAM.gov v2 search. `https://api.sam.gov/opportunities/v2/search?api_key=...&postedFrom=...&naicsCode=...&keywords=...`

**Fallback policy (PRD §5.4):** SAM 429 / 5xx → fall back to `load_seeded_opportunities`. Mark step `degraded`.

- [ ] **Step 1: Write tests with httpx mock**

```python
import httpx
import pytest
from api.skills.search_sam.skill import SearchSamSkill, SearchSamInput

@pytest.mark.asyncio
async def test_happy_path_returns_normalized_opportunities(respx_mock):
    respx_mock.get("https://api.sam.gov/opportunities/v2/search").respond(
        200, json={"opportunitiesData": [{
            "title": "Cloud Services", "noticeId": "ABC-001",
            "fullParentPathName": "DOD", "naicsCode": "541512",
            "typeOfSetAsideDescription": "Total Small Business",
            "responseDeadLine": "2026-06-15T17:00:00",
            "uiLink": "https://sam.gov/opp/abc",
            "description": "...",
        }]}
    )
    skill = SearchSamSkill(api_key="test", http=httpx.AsyncClient())
    out = await skill.run(SearchSamInput(keywords="cloud", naics="541512"))
    assert len(out.opportunities) == 1
    assert out.opportunities[0]["solicitation_number"] == "ABC-001"
    assert out.degraded is False

@pytest.mark.asyncio
async def test_429_returns_degraded_with_empty_results(respx_mock):
    respx_mock.get("https://api.sam.gov/opportunities/v2/search").respond(429)
    skill = SearchSamSkill(api_key="test", http=httpx.AsyncClient())
    out = await skill.run(SearchSamInput(keywords="x"))
    assert out.degraded is True
    assert out.opportunities == []
    assert "rate limit" in out.error.lower()
```

- [ ] **Step 2: Add `respx` to dev deps**

```toml
# pyproject.toml [project.optional-dependencies].dev
"respx>=0.21",
```

```bash
uv sync --all-extras
```

- [ ] **Step 3: Implement**

```python
"""search_sam_opportunities — SAM.gov v2 search with degraded-fallback."""
from __future__ import annotations
from dataclasses import dataclass, field
import httpx

SAM_URL = "https://api.sam.gov/opportunities/v2/search"

@dataclass
class SearchSamInput:
    keywords: str = ""
    naics: str | None = None
    posted_from: str | None = None  # MM/dd/yyyy
    set_aside: str | None = None
    state: str | None = None
    limit: int = 20

@dataclass
class SearchSamOutput:
    opportunities: list[dict] = field(default_factory=list)
    degraded: bool = False
    error: str = ""

class SearchSamSkill:
    def __init__(self, api_key: str, http: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._http = http

    async def run(self, payload: SearchSamInput) -> SearchSamOutput:
        params = {
            "api_key": self._api_key,
            "limit": payload.limit,
            "q": payload.keywords or "",
        }
        if payload.naics:
            params["naicsCode"] = payload.naics
        if payload.posted_from:
            params["postedFrom"] = payload.posted_from
        if payload.set_aside:
            params["typeOfSetAside"] = payload.set_aside
        if payload.state:
            params["state"] = payload.state
        try:
            resp = await self._http.get(SAM_URL, params=params, timeout=20.0)
        except httpx.HTTPError as e:
            return SearchSamOutput(degraded=True, error=f"network: {e}")
        if resp.status_code == 429:
            return SearchSamOutput(degraded=True, error="SAM rate limit (429)")
        if resp.status_code >= 500:
            return SearchSamOutput(degraded=True, error=f"SAM 5xx: {resp.status_code}")
        if resp.status_code >= 400:
            return SearchSamOutput(degraded=True, error=f"SAM client error: {resp.status_code}")
        data = resp.json()
        normalized = [self._normalize(rec) for rec in data.get("opportunitiesData", [])]
        return SearchSamOutput(opportunities=normalized)

    @staticmethod
    def _normalize(rec: dict) -> dict:
        return {
            "title": rec.get("title", ""),
            "agency": rec.get("fullParentPathName", "").split(".")[0],
            "solicitation_number": rec.get("noticeId", ""),
            "source_url": rec.get("uiLink", ""),
            "due_date": (rec.get("responseDeadLine") or "")[:10],
            "naics": rec.get("naicsCode", ""),
            "set_aside": rec.get("typeOfSetAsideDescription", "") or "None",
            "place_of_performance": rec.get("placeOfPerformance", {}).get("city", {}).get("name", ""),
            "description": (rec.get("description") or "")[:1000],
            "attachments": [],
            "raw_payload": rec,
        }
```

- [ ] **Step 4: Run, commit**

```bash
uv run pytest api/tests/test_search_sam.py -v
git add api/skills/search_sam/ api/tests/test_search_sam.py pyproject.toml uv.lock
git commit -m "feat(skills): A11 search_sam_opportunities with degraded fallback"
```

---

### Task 3.2: fetch_attachment skill

**Why:** Download a PDF from a URL (sam.gov uiLink → "Resources" attachment URL) into Supabase Storage at `raw/<run_id>/<filename>.pdf`. Returns the storage path so `parse_pdf` can pick it up.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/skills/fetch_attachment/skill.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/fetch_attachment/__init__.py`
- Create: `/Volumes/CS_Stuff/govcon/api/tests/test_fetch_attachment.py`

- [ ] **Step 1: Write test (mocked Storage + httpx)**

```python
import httpx, pytest
from api.skills.fetch_attachment.skill import FetchAttachmentSkill, FetchAttachmentInput

@pytest.mark.asyncio
async def test_downloads_and_uploads_to_storage(respx_mock):
    respx_mock.get("https://example.gov/rfp.pdf").respond(200, content=b"%PDF-1.4...")
    storage = _FakeStorage()
    skill = FetchAttachmentSkill(http=httpx.AsyncClient(), storage=storage)
    out = await skill.run(FetchAttachmentInput(
        run_id="abc", url="https://example.gov/rfp.pdf",
    ))
    assert out.storage_path == "raw/abc/rfp.pdf"
    assert storage.uploaded == [("raw/abc/rfp.pdf", b"%PDF-1.4...")]

class _FakeStorage:
    def __init__(self): self.uploaded = []
    async def upload(self, path: str, body: bytes) -> str:
        self.uploaded.append((path, body))
        return path
```

- [ ] **Step 2: Implement**

```python
"""fetch_attachment — download PDF and persist to Supabase Storage raw bucket."""
from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlparse
import httpx
from api.storage import StorageClient

@dataclass
class FetchAttachmentInput:
    run_id: str
    url: str
    filename: str | None = None

@dataclass
class FetchAttachmentOutput:
    storage_path: str
    bytes_downloaded: int

class FetchAttachmentSkill:
    def __init__(self, http: httpx.AsyncClient, storage: StorageClient) -> None:
        self._http = http
        self._storage = storage

    async def run(self, payload: FetchAttachmentInput) -> FetchAttachmentOutput:
        resp = await self._http.get(payload.url, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()
        body = resp.content
        filename = payload.filename or self._derive_name(payload.url)
        path = f"raw/{payload.run_id}/{filename}"
        await self._storage.upload(path, body)
        return FetchAttachmentOutput(storage_path=path, bytes_downloaded=len(body))

    @staticmethod
    def _derive_name(url: str) -> str:
        parsed = urlparse(url).path
        name = parsed.rsplit("/", 1)[-1] or "attachment.pdf"
        return name if name.lower().endswith(".pdf") else f"{name}.pdf"
```

- [ ] **Step 3: Run, commit**

```bash
uv run pytest api/tests/test_fetch_attachment.py -v
git add api/skills/fetch_attachment/ api/tests/test_fetch_attachment.py
git commit -m "feat(skills): fetch_attachment — download PDF to Supabase Storage raw/"
```

---

### Task 3.3: parse_goal skill

**Why:** Capture Lead first move. Convert `"Find cybersecurity opportunities we can pursue in the next 60 days"` → structured search criteria (keywords, naics_hints, due-date window, set_aside_pref, geography).

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/skills/parse_goal/skill.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/parse_goal/__init__.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/parse_goal/prompt.txt`
- Create: `/Volumes/CS_Stuff/govcon/api/tests/test_parse_goal.py`

- [ ] **Step 1: Test**

```python
import pytest
from api.skills.parse_goal.skill import ParseGoalSkill, ParseGoalInput
from api.tests.fakes import FakeLLM

@pytest.mark.asyncio
async def test_parses_typical_goal():
    fake_llm = FakeLLM(canned_response={
        "keywords": ["cybersecurity", "infosec"],
        "naics_hints": ["541512", "541519"],
        "due_window_days": 60,
        "set_aside_pref": "small_business",
        "geography": None,
        "agencies": None,
        "opportunity_type": "any",
    })
    skill = ParseGoalSkill(llm=fake_llm)
    out = await skill.run(ParseGoalInput(
        goal="Find cybersecurity opportunities we can pursue in the next 60 days.",
        company_profile={"name": "DemoCo", "naics_codes": ["541512"]},
    ))
    assert "cybersecurity" in out.keywords
    assert out.due_window_days == 60
```

- [ ] **Step 2: Prompt**

```
You parse a small business owner's contracting goal into structured search criteria.

Always return JSON with these fields (use null when unknown):
- keywords: list of 3-8 strings
- naics_hints: list of NAICS codes (strings) — empty if none implied
- due_window_days: integer — interpret "next N days/weeks/months", default 30
- set_aside_pref: "small_business" | "8a" | "wosb" | "hubzone" | "sdvosb" | null
- geography: state code or city name | null
- agencies: list of agency names mentioned | null
- opportunity_type: "any" | "rfp" | "rfi" | "sources_sought"

Be conservative. If unclear, leave null.
```

- [ ] **Step 3: Implement**

```python
"""parse_goal — natural-language goal → structured search criteria."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from api.llm import LLMClient, LLMMetrics

PROMPT = (Path(__file__).parent / "prompt.txt").read_text()

@dataclass
class ParseGoalInput:
    goal: str
    company_profile: dict

@dataclass
class ParseGoalOutput:
    keywords: list[str]
    naics_hints: list[str]
    due_window_days: int
    set_aside_pref: str | None
    geography: str | None
    agencies: list[str] | None
    opportunity_type: str
    metrics: LLMMetrics

class ParseGoalSkill:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def run(self, payload: ParseGoalInput) -> ParseGoalOutput:
        result, metrics = await self._llm.generate_structured(
            system=PROMPT,
            user=f"Goal: {payload.goal}\nCompany NAICS: {payload.company_profile.get('naics_codes', [])}",
            schema={
                "type": "object",
                "required": ["keywords", "naics_hints", "due_window_days", "opportunity_type"],
                "properties": {
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "naics_hints": {"type": "array", "items": {"type": "string"}},
                    "due_window_days": {"type": "integer", "minimum": 1, "maximum": 365},
                    "set_aside_pref": {"type": ["string", "null"]},
                    "geography": {"type": ["string", "null"]},
                    "agencies": {"type": ["array", "null"]},
                    "opportunity_type": {"type": "string"},
                },
            },
        )
        return ParseGoalOutput(**result, metrics=metrics)
```

- [ ] **Step 4: Run, commit**

```bash
uv run pytest api/tests/test_parse_goal.py -v
git add api/skills/parse_goal/ api/tests/test_parse_goal.py
git commit -m "feat(skills): parse_goal — natural-language goal → search criteria"
```

---

### Task 3.4: rank_opportunities skill

**Why:** After Capture Lead has scored several opportunities, rank them. Pure deterministic — no LLM. Sort by `(decision_band_priority, total_score desc, due_date asc)`.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/skills/rank_opportunities/skill.py`
- Create: `/Volumes/CS_Stuff/govcon/api/skills/rank_opportunities/__init__.py`
- Create: `/Volumes/CS_Stuff/govcon/api/tests/test_rank_opportunities.py`

- [ ] **Step 1: Test**

```python
from api.skills.rank_opportunities.skill import RankOpportunitiesSkill, RankInput

def test_ranks_by_band_then_score_then_deadline():
    skill = RankOpportunitiesSkill()
    scored = [
        {"opportunity_id": "a", "decision": "maybe", "total_score": 60, "due_date": "2026-06-01"},
        {"opportunity_id": "b", "decision": "strong_pursue", "total_score": 88, "due_date": "2026-07-01"},
        {"opportunity_id": "c", "decision": "strong_pursue", "total_score": 92, "due_date": "2026-08-01"},
        {"opportunity_id": "d", "decision": "reject", "total_score": 0, "due_date": "2026-05-15"},
    ]
    out = skill.run(RankInput(scored=scored))
    assert [r["opportunity_id"] for r in out.ranked] == ["c", "b", "a", "d"]
```

- [ ] **Step 2: Implement**

```python
"""rank_opportunities — deterministic ordering for the timeline UI."""
from __future__ import annotations
from dataclasses import dataclass

BAND_ORDER = {"strong_pursue": 0, "pursue": 1, "maybe": 2, "reject": 3}

@dataclass
class RankInput:
    scored: list[dict]

@dataclass
class RankOutput:
    ranked: list[dict]

class RankOpportunitiesSkill:
    def run(self, payload: RankInput) -> RankOutput:
        return RankOutput(ranked=sorted(
            payload.scored,
            key=lambda x: (
                BAND_ORDER.get(x.get("decision"), 99),
                -int(x.get("total_score", 0)),
                x.get("due_date", "9999-12-31"),
            ),
        ))
```

- [ ] **Step 3: Run, commit**

```bash
uv run pytest api/tests/test_rank_opportunities.py -v
git add api/skills/rank_opportunities/ api/tests/test_rank_opportunities.py
git commit -m "feat(skills): rank_opportunities — deterministic band-then-score ordering"
```

---

# PHASE 4 — Hermes Integration (A9 + A10)

The biggest unknown. Decide process boundary first; integrate runtime; bridge events; register skill manifest; replace replayer.

---

### Task 4.1: Hermes process boundary spike

**Why:** Two viable architectures (HERMES.md sketches both):
- **A: in-process** — `from hermes_agent import Agent` inside FastAPI, agent.run() in a background task. Simplest, but Hermes' subprocess sandbox vs FastAPI's event loop must be reconciled.
- **B: subprocess** — Hermes as a child process; FastAPI talks to it over Unix socket / stdin-stdout JSON-RPC. Cleaner isolation, more code.

Decision criteria: how does hermes-agent (Nous Research, ~v0.13.0 per STANDUP) actually package its planner loop? If it requires owning the asyncio loop, B. If it exposes an async-friendly Agent class, A.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/tasks/HERMES_SPIKE.md` — record findings
- Create: `/Volumes/CS_Stuff/govcon/spike/hermes_inproc.py` — minimal A spike
- Create: `/Volumes/CS_Stuff/govcon/spike/hermes_subproc.py` — minimal B spike

- [ ] **Step 1: Read hermes-agent's actual API**

```bash
uv run python -c "import hermes_agent; help(hermes_agent.Agent)" 2>&1 | head -100
ls $(python -c "import hermes_agent, os; print(os.path.dirname(hermes_agent.__file__))")
```

- [ ] **Step 2: Write spike A (in-process)**

`spike/hermes_inproc.py`:

```python
"""Spike: can we run Hermes inside our FastAPI event loop?"""
import asyncio
from hermes_agent import Agent  # adjust to actual API

async def main() -> None:
    agent = Agent(model="claude-haiku-4-5-20251001", skills=[])
    result = await agent.run("Say hello.")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

```bash
uv run python spike/hermes_inproc.py
```

- [ ] **Step 3: Write spike B (subprocess)**

`spike/hermes_subproc.py` — subprocess.Popen with JSON over stdin/stdout.

- [ ] **Step 4: Document decision in HERMES_SPIKE.md**

Include: which spike worked, latency, memory, error-handling story, trace event surface (does Hermes already emit JSON to stderr that we can parse?).

- [ ] **Step 5: Commit spike + decision**

```bash
git add spike/ tasks/HERMES_SPIKE.md
git commit -m "spike(hermes): evaluate in-process vs subprocess integration"
```

> **Branch in plan:** Tasks 4.2-4.5 below assume **in-process** (likely outcome). If subprocess wins, the runner becomes a `subprocess.Popen` wrapper and the bridge reads from its stdout — same downstream contract.

---

### Task 4.2: hermes_runner — start agent + register skills

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/agent/hermes_runner.py`
- Create: `/Volumes/CS_Stuff/govcon/api/agent/skill_registry.py`

- [ ] **Step 1: Skill registry — wraps each skill with input/output JSON schemas**

`api/agent/skill_registry.py`:

```python
"""Build the Hermes tool registry from our domain skills."""
from __future__ import annotations
from typing import Any
from api.skills.parse_pdf import ParsePdfSkill
from api.skills.extract_requirements import ExtractRequirementsSkill
from api.skills.score_fit import ScoreFitSkill
from api.skills.detect_risks import DetectRisksSkill
from api.skills.generate_action_package import GenerateActionPackageSkill
from api.skills.search_sam import SearchSamSkill
from api.skills.fetch_attachment import FetchAttachmentSkill
from api.skills.parse_goal import ParseGoalSkill
from api.skills.rank_opportunities import RankOpportunitiesSkill
from api.skills.load_seeded_opportunities import LoadSeededSkill

def build_skill_manifest(deps: dict[str, Any]) -> list[dict]:
    """Each entry: {name, description, input_schema, output_schema, callable}."""
    return [
        {"name": "parse_goal", "callable": ParseGoalSkill(deps["llm"]),
         "description": "Convert natural-language goal to structured search criteria.",
         "input_schema": {...}, "output_schema": {...}},
        {"name": "search_sam", "callable": SearchSamSkill(deps["sam_api_key"], deps["http"]),
         "description": "Query SAM.gov v2 search API.",
         "input_schema": {...}, "output_schema": {...}},
        {"name": "load_seeded_opportunities",
         "callable": LoadSeededSkill(deps["opp_repo"], deps["fixtures_dir"]),
         "description": "Load seeded fixture opportunities.", ...},
        {"name": "fetch_attachment",
         "callable": FetchAttachmentSkill(deps["http"], deps["storage"]),
         "description": "Download PDF to Supabase Storage.", ...},
        {"name": "parse_pdf", "callable": ParsePdfSkill(),
         "description": "Extract page-level text from PDF.", ...},
        {"name": "extract_requirements",
         "callable": ExtractRequirementsSkill(deps["llm"]),
         "description": "Extract structured requirements from parsed PDF chunks.", ...},
        {"name": "score_fit", "callable": ScoreFitSkill(deps["llm"]),
         "description": "Score opportunity fit with §11.1 short-circuit.", ...},
        {"name": "detect_risks", "callable": DetectRisksSkill(deps["llm"]),
         "description": "Detect risks per §5.8 taxonomy.", ...},
        {"name": "generate_action_package",
         "callable": GenerateActionPackageSkill(deps["llm"]),
         "description": "Synthesize action package (modes: full, reject_summary).", ...},
        {"name": "rank_opportunities", "callable": RankOpportunitiesSkill(),
         "description": "Order scored opportunities for the timeline.", ...},
    ]
```

(Fill `input_schema` / `output_schema` from each skill's dataclass — convert to JSON Schema with a small helper.)

- [ ] **Step 2: hermes_runner.py — orchestrate one run**

```python
"""Start a Hermes agent for a run and bridge its events to Redis."""
from __future__ import annotations
import asyncio
from uuid import UUID
from api.agent.skill_registry import build_skill_manifest
from api.agent.hermes_bridge import bridge_events_to_redis
from api.config import settings
# Adjust import to actual hermes-agent API (see Task 4.1):
from hermes_agent import Agent

async def run_capture(
    run_id: UUID, goal: str, company_profile: dict, deps: dict
) -> None:
    skills = build_skill_manifest(deps)
    agent = Agent(
        model=settings.hermes_model,
        skills=skills,
        max_steps=settings.run_budget_steps,
        max_cost_usd=settings.run_budget_usd,
        max_seconds=settings.run_budget_seconds,
    )
    # Hermes emits events on agent.events (async iterator) — adjust to actual API.
    bridge_task = asyncio.create_task(
        bridge_events_to_redis(run_id, agent.events, deps["redis"])
    )
    try:
        await agent.run(
            objective=goal,
            context={"company_profile": company_profile, "run_id": str(run_id)},
        )
    finally:
        await bridge_task
```

- [ ] **Step 3: Tests stubbing the Hermes Agent**

`api/tests/test_hermes_runner.py` — mock the Hermes Agent class, verify skills passed in, verify event bridge wired.

- [ ] **Step 4: Commit**

```bash
git add api/agent/skill_registry.py api/agent/hermes_runner.py api/tests/test_hermes_runner.py
git commit -m "feat(agent): A9 hermes_runner — build skill manifest, orchestrate one run"
```

---

### Task 4.3: hermes_bridge — translate events to CONTRACTS.md §3 SSE

**Why:** Hermes emits its own internal trace primitives. Our frontend depends on the locked CONTRACTS.md §3 schema (8 event types). Bridge translates 1:N.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/agent/hermes_bridge.py`
- Create: `/Volumes/CS_Stuff/govcon/api/tests/test_hermes_bridge.py`

- [ ] **Step 1: Tests**

```python
import pytest, json
from api.agent.hermes_bridge import translate

def test_translate_step_start_to_step_started():
    hermes_event = {"kind": "step.start", "step_id": "s1",
                    "label": "search opportunities", "timestamp": "2026-05-09T12:00:00Z"}
    out = translate(hermes_event, run_id="run-1")
    assert out["type"] == "step_started"
    assert out["step_id"] == "s1"
    assert out["label"] == "search opportunities"
    assert out["run_id"] == "run-1"

def test_translate_tool_call_to_tool_called():
    he = {"kind": "tool.call", "step_id": "s2", "tool": "parse_pdf",
          "input": {"path": "x.pdf"}, "rationale": "need to extract text",
          "timestamp": "2026-05-09T12:00:01Z"}
    out = translate(he, run_id="run-1")
    assert out["type"] == "tool_called"
    assert out["tool"] == "parse_pdf"

def test_translate_subagent_spawn_emits_subagent_event():
    he = {"kind": "agent.spawn", "agent_role": "capture_analyst",
          "child_id": "ca-1", "parent_id": "cl-0",
          "timestamp": "2026-05-09T12:00:02Z"}
    out = translate(he, run_id="run-1")
    assert out["type"] == "subagent_spawned"
    assert out["agent_role"] == "capture_analyst"

def test_unknown_event_returns_none():
    he = {"kind": "telemetry.gauge", "name": "x", "value": 1}
    assert translate(he, run_id="run-1") is None
```

- [ ] **Step 2: Implement bridge + Redis publisher**

```python
"""Translate Hermes internal trace events to CONTRACTS.md §3 wire shapes."""
from __future__ import annotations
import json
from typing import AsyncIterator
from uuid import UUID
import redis.asyncio as aioredis

EVENT_MAP = {
    "run.start": "run_started",
    "run.complete": "run_completed",
    "step.start": "step_started",
    "step.complete": "step_completed",
    "tool.call": "tool_called",
    "tool.return": "tool_returned",
    "decision.opportunity_ranked": "opportunity_ranked",
    "human.review_requested": "needs_human",
    "agent.spawn": "subagent_spawned",
    "agent.complete": "subagent_completed",
}

def translate(hermes_event: dict, run_id: str) -> dict | None:
    kind = hermes_event.get("kind", "")
    out_type = EVENT_MAP.get(kind)
    if not out_type:
        return None
    base = {"type": out_type, "run_id": run_id, "ts": hermes_event.get("timestamp", "")}
    if out_type in {"step_started", "step_completed"}:
        base["step_id"] = hermes_event["step_id"]
        if out_type == "step_started":
            base["label"] = hermes_event.get("label", "")
        else:
            base["status"] = hermes_event.get("status", "complete")
    elif out_type == "tool_called":
        base.update({
            "step_id": hermes_event["step_id"],
            "tool": hermes_event["tool"],
            "input": hermes_event.get("input", {}),
            "rationale": hermes_event.get("rationale", ""),
        })
    elif out_type == "tool_returned":
        base.update({
            "step_id": hermes_event["step_id"],
            "tool": hermes_event["tool"],
            "output": hermes_event.get("output"),
            "error": hermes_event.get("error"),
            "latency_ms": hermes_event.get("latency_ms", 0),
            "cost_usd": hermes_event.get("cost_usd", 0.0),
        })
    elif out_type == "opportunity_ranked":
        base.update({
            "opportunity_id": hermes_event["opportunity_id"],
            "score": hermes_event["score"],
            "decision": hermes_event["decision"],
        })
    elif out_type == "needs_human":
        base.update({
            "question": hermes_event.get("question", ""),
            "context": hermes_event.get("context", {}),
        })
    elif out_type in {"subagent_spawned", "subagent_completed"}:
        base.update({
            "agent_role": hermes_event.get("agent_role"),
            "child_id": hermes_event.get("child_id"),
            "parent_id": hermes_event.get("parent_id"),
        })
        if out_type == "subagent_completed":
            base["status"] = hermes_event.get("status", "complete")
    elif out_type == "run_started":
        base.update({"goal": hermes_event.get("goal", ""),
            "profile_id": hermes_event.get("profile_id", "")})
    elif out_type == "run_completed":
        base.update({"status": hermes_event.get("status", "complete"),
            "summary": hermes_event.get("summary", "")})
    return base

async def bridge_events_to_redis(
    run_id: UUID,
    events: AsyncIterator[dict],
    redis_client: aioredis.Redis,
) -> None:
    channel = f"agent-run:{run_id}"
    async for hermes_event in events:
        translated = translate(hermes_event, run_id=str(run_id))
        if translated is None:
            continue
        await redis_client.publish(channel, json.dumps(translated))
        if translated["type"] == "run_completed":
            break
```

- [ ] **Step 3: Extend trace-event schema for subagent events**

Add to `/Volumes/CS_Stuff/govcon/schemas/trace-event.schema.json` `oneOf` array:

```json
{
  "type": "object",
  "required": ["type", "run_id", "agent_role", "child_id", "parent_id", "ts"],
  "properties": {
    "type": {"const": "subagent_spawned"},
    "run_id": {"type": "string"},
    "agent_role": {"enum": ["capture_lead", "capture_analyst",
        "compliance_officer", "risk_analyst", "proposal_strategist"]},
    "child_id": {"type": "string"},
    "parent_id": {"type": "string"},
    "ts": {"type": "string"}
  }
},
{
  "type": "object",
  "required": ["type", "run_id", "child_id", "status", "ts"],
  "properties": {
    "type": {"const": "subagent_completed"},
    "run_id": {"type": "string"},
    "child_id": {"type": "string"},
    "status": {"enum": ["complete", "failed", "timeout"]},
    "ts": {"type": "string"}
  }
}
```

- [ ] **Step 4: Run, regenerate schemas, commit**

```bash
uv run pytest api/tests/test_hermes_bridge.py -v
make schemas  # regenerate Pydantic
git add api/agent/hermes_bridge.py api/tests/test_hermes_bridge.py schemas/trace-event.schema.json api/schemas/
git commit -m "feat(agent): hermes_bridge — translate Hermes events to CONTRACTS.md §3 SSE"
```

---

### Task 4.4: Wire skill personas (5 agents per AGENT_ARCHITECTURE.md)

**Why:** Each agent role has a distinct persona, tool whitelist, and delegation rules. Implement per `~/.hermes/skills/govcapture/` skill manifests.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/.hermes/skills/govcapture/operate_bid_desk.md`
- Create: `/Volumes/CS_Stuff/govcon/.hermes/skills/govcapture/discover_opportunities.md`
- Create: `/Volumes/CS_Stuff/govcon/.hermes/skills/govcapture/analyze_opportunity_e2e.md`
- Create: `/Volumes/CS_Stuff/govcon/.hermes/skills/govcapture/extract_requirements_with_evidence.md`
- Create: `/Volumes/CS_Stuff/govcon/.hermes/skills/govcapture/score_fit_with_eligibility_check.md`
- Create: `/Volumes/CS_Stuff/govcon/.hermes/skills/govcapture/detect_risks_calibrated.md`
- Create: `/Volumes/CS_Stuff/govcon/.hermes/skills/govcapture/generate_full_action_package.md`
- Create: `/Volumes/CS_Stuff/govcon/.hermes/skills/govcapture/generate_reject_summary.md`

- [ ] **Step 1: Author each manifest**

Each `.md` file follows the Hermes skill format (frontmatter + body). Example for `operate_bid_desk.md`:

```markdown
---
name: operate_bid_desk
description: Root operator for the GovCon Bid Desk — receives a goal + profile, produces ranked opportunities + action packages.
agents: [capture_lead]
tools: [parse_goal, search_sam, load_seeded_opportunities, rank_opportunities]
delegates_to: [discover_opportunities, analyze_opportunity_e2e]
---

You are the Capture Lead. Given a company profile and goal:
1. Call parse_goal to structure the search criteria.
2. Call search_sam (fall back to load_seeded_opportunities if degraded).
3. For each top-3 opportunity, delegate to analyze_opportunity_e2e.
4. Collect results, call rank_opportunities, return a summary.

Budgets: respect max_steps, max_cost_usd, max_seconds. If budget pressure, score top-3 deeply and summarize the rest.
```

Repeat for each role. The reject-mode strategist:

```markdown
---
name: generate_reject_summary
description: Deterministic slim action package for reject-decision opportunities. NO LLM call.
tools: [generate_action_package]
---

Call generate_action_package with mode="reject_summary". Do not LLM. Do not embellish.
```

- [ ] **Step 2: Update .hermes/config.yaml for max_spawn_depth=2**

Verify config.yaml has:

```yaml
delegation:
  max_spawn_depth: 2
  max_concurrent_children: 3
  orchestrator_enabled: true
skills:
  search_paths:
    - ~/.hermes/skills/govcapture
```

- [ ] **Step 3: Commit**

```bash
git add .hermes/skills/govcapture/ .hermes/config.yaml
git commit -m "feat(agent): wire 5-agent personas with delegation + tool whitelists"
```

---

### Task 4.5: Replace replay.py call site with hermes_runner

**Files:**
- Modify: `/Volumes/CS_Stuff/govcon/api/routes/agent_runs.py` lines ~51-60
- Modify: `/Volumes/CS_Stuff/govcon/api/tests/test_routes.py` SSE test

- [ ] **Step 1: Update route handler**

In `api/routes/agent_runs.py`:

```python
# BEFORE:
# background_tasks.add_task(replay_example_run, run.id)
# AFTER:
from api.agent.hermes_runner import run_capture
background_tasks.add_task(
    run_capture,
    run_id=run.id,
    goal=payload.goal,
    company_profile=profile.model_dump(),
    deps={
        "llm": llm_client,
        "redis": redis_client,
        "storage": storage_client,
        "http": http_client,
        "opp_repo": opp_repo,
        "fixtures_dir": Path("fixtures"),
        "sam_api_key": settings.sam_api_key,
    },
)
```

- [ ] **Step 2: Add fallback flag — DEMO_USE_SEEDED_ONLY**

In runner, if `settings.demo_use_seeded_only`, the planner is told to skip search_sam and only call load_seeded_opportunities. Pass this as part of the agent context.

- [ ] **Step 3: Update SSE test to mock hermes_runner**

Replace the existing replay-based SSE test with one that mocks `run_capture` and publishes a known sequence of events to Redis. Verify SSE stream framing.

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest -v
```
Expected: all green (replayer-based tests removed, hermes-mocked SSE test added).

- [ ] **Step 5: Commit + delete dead replayer**

```bash
git rm api/agent/replay.py
git add api/routes/agent_runs.py api/tests/test_routes.py
git commit -m "feat(agent): A9 replace replayer with hermes_runner; delete pre-A9 replay.py"
```

---

### Task 4.6: A10 request_human_review — pause-and-resume flow

**Why:** When confidence collapses or §5.13 sensitive action is needed, agent pauses. Run state moves to `awaiting_review`. Frontend shows the question + context. User answers via `POST /agent-runs/{id}/resume` → run resumes with the answer in context.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/skills/request_human_review/skill.py`
- Modify: `/Volumes/CS_Stuff/govcon/api/db/models.py` — add `paused_at`, `pending_question`, `pending_context` to `agent_runs`
- Create: Alembic migration `0003_human_review.py`
- Modify: `/Volumes/CS_Stuff/govcon/api/routes/agent_runs.py` — add POST `/{id}/resume`
- Test: `/Volumes/CS_Stuff/govcon/api/tests/test_human_review.py`

- [ ] **Step 1: Add migration**

```bash
make migration MSG="add human review pause fields to agent_runs"
```

Edit the generated migration to add columns:
- `paused_at: TIMESTAMP NULL`
- `pending_question: TEXT NULL`
- `pending_context: JSONB NULL`
- `human_response: JSONB NULL`

- [ ] **Step 2: Implement skill (writes to DB, emits needs_human event)**

```python
"""request_human_review — halt run, surface question to user."""
from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID
from api.repositories.agent_run import AgentRunRepo

@dataclass
class RequestHumanReviewInput:
    run_id: UUID
    question: str
    context: dict

@dataclass
class RequestHumanReviewOutput:
    paused: bool

class RequestHumanReviewSkill:
    def __init__(self, agent_run_repo: AgentRunRepo) -> None:
        self._repo = agent_run_repo

    async def run(self, payload: RequestHumanReviewInput) -> RequestHumanReviewOutput:
        await self._repo.pause_for_review(
            run_id=payload.run_id,
            question=payload.question,
            context=payload.context,
        )
        return RequestHumanReviewOutput(paused=True)
```

- [ ] **Step 3: Add resume endpoint**

```python
# api/routes/agent_runs.py
@router.post("/{run_id}/resume", status_code=200)
async def resume_run(
    run_id: UUID,
    payload: ResumeRunRequest,  # {"answer": dict}
    repo: AgentRunRepo = Depends(...),
    background_tasks: BackgroundTasks,
) -> dict:
    run = await repo.get(run_id)
    if not run or not run.paused_at:
        raise HTTPException(409, "Run is not paused.")
    await repo.record_human_response(run_id, payload.answer)
    background_tasks.add_task(resume_capture, run_id=run_id, answer=payload.answer, ...)
    return {"resumed": True}
```

- [ ] **Step 4: Test the full pause/resume cycle**

```python
@pytest.mark.asyncio
async def test_request_human_review_pauses_run(client, db_session):
    # ... seed run ...
    # invoke skill
    # verify run.paused_at is set
    # POST /agent-runs/{id}/resume
    # verify run.paused_at cleared, human_response stored
```

- [ ] **Step 5: Commit**

```bash
git add api/skills/request_human_review/ api/migrations/versions/0003_*.py \
        api/db/models.py api/routes/agent_runs.py api/tests/test_human_review.py
git commit -m "feat(skills): A10 request_human_review with pause/resume API"
```

---

# PHASE 5 — Eval Harness (A12)

PRD §19. Per-fixture golden assertions. `make eval` is the pre-demo smoke test.

---

### Task 5.1: Eval runner skeleton

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/eval/runner/__init__.py`
- Create: `/Volumes/CS_Stuff/govcon/eval/runner/run.py`
- Create: `/Volumes/CS_Stuff/govcon/eval/runner/assertions.py`
- Create: `/Volumes/CS_Stuff/govcon/eval/goldens/strong-pursue.json` (will fill via Task 5.2)
- Create: `/Volumes/CS_Stuff/govcon/eval/goldens/maybe.json`
- Create: `/Volumes/CS_Stuff/govcon/eval/goldens/reject.json`
- Create: `/Volumes/CS_Stuff/govcon/eval/goldens/adversarial-image-pdf.json`
- Modify: `/Volumes/CS_Stuff/govcon/Makefile` — add `eval` target

- [ ] **Step 1: Runner**

```python
"""Eval runner — load fixtures, run skills, assert against goldens."""
from __future__ import annotations
import asyncio, json
from pathlib import Path
from api.skills.parse_pdf import ParsePdfSkill, ParsePdfInput
from api.skills.extract_requirements import ExtractRequirementsSkill, ExtractRequirementsInput
from api.skills.score_fit import ScoreFitSkill, ScoreFitInput
from api.skills.detect_risks import DetectRisksSkill, DetectRisksInput
from api.skills.generate_action_package import (
    GenerateActionPackageSkill, GenerateActionPackageInput,
)
from api.llm import LLMClient
from eval.runner.assertions import assert_fixture
from api.config import settings

DEMO_COMPANY = {
    "name": "DemoCo", "naics_codes": ["541512"],
    "certifications": ["CMMC L2"], "small_business_status": True,
    "clearance_status": "none",
    "capabilities": ["cloud migration", "AWS GovCloud", "DevSecOps"],
}

async def run_one(slug: str, fixtures_dir: Path, goldens_dir: Path) -> dict:
    manifest = json.loads((fixtures_dir / slug / "manifest.json").read_text())
    pdf_path = fixtures_dir / slug / "attachments" / manifest["attachments"][0]["filename"]
    llm = LLMClient(api_key=settings.anthropic_api_key, model=settings.llm_dev_model)

    parsed = await ParsePdfSkill().run(ParsePdfInput(path=str(pdf_path)))
    if parsed.unparseable:
        # Adversarial path
        return {"unparseable": True}

    reqs_out = await ExtractRequirementsSkill(llm).run(
        ExtractRequirementsInput(parsed_chunks=parsed.chunks))
    score_out = await ScoreFitSkill(llm).run(ScoreFitInput(
        company_profile=DEMO_COMPANY,
        requirements=[r.__dict__ for r in reqs_out.requirements]))
    risks_out = await DetectRisksSkill(llm).run(DetectRisksInput(
        company_profile=DEMO_COMPANY,
        requirements=[r.__dict__ for r in reqs_out.requirements],
        opportunity=manifest["opportunity"]))

    mode = "reject_summary" if score_out.decision == "reject" else "full"
    pkg_out = await GenerateActionPackageSkill(llm).run(GenerateActionPackageInput(
        mode=mode, company_profile=DEMO_COMPANY,
        opportunity=manifest["opportunity"],
        requirements=[r.__dict__ for r in reqs_out.requirements],
        fit_score=score_out.__dict__,
        risks=[r.__dict__ for r in risks_out.risks]))

    actual = {
        "decision": score_out.decision,
        "total_score": score_out.total_score,
        "blockers": score_out.blockers,
        "requirement_count": len(reqs_out.requirements),
        "risk_count": len(risks_out.risks),
        "package_sections_present": [
            "executive_summary" if pkg_out.executive_summary else None,
            "compliance_matrix" if pkg_out.compliance_matrix else None,
            "approval" if pkg_out.human_approval_required else None,
        ],
    }
    return actual

async def main() -> int:
    fixtures = Path("fixtures")
    goldens = Path("eval/goldens")
    failures = 0
    for slug in ["strong-pursue", "maybe", "reject", "adversarial-image-pdf"]:
        manifest = json.loads((fixtures / slug / "manifest.json").read_text())
        actual = await run_one(slug, fixtures, goldens)
        try:
            assert_fixture(slug, manifest, actual)
            print(f"✓ {slug}")
        except AssertionError as e:
            print(f"✗ {slug}: {e}")
            failures += 1
    return failures

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

- [ ] **Step 2: Assertions**

```python
"""Eval assertions per PRD §19."""
def assert_fixture(slug: str, manifest: dict, actual: dict) -> None:
    expected_band = manifest["expected_decision_band"]
    if slug == "adversarial-image-pdf":
        assert actual.get("unparseable") is True, "adversarial fixture must be unparseable"
        return
    # Decision band
    assert actual["decision"] == expected_band, \
        f"decision {actual['decision']} != expected {expected_band}"
    # §11.1 reject short-circuit
    if expected_band == "reject":
        assert actual["total_score"] == 0, "reject fixture must score 0 (§11.1)"
        for blocker in manifest.get("expected_critical_blockers", []):
            assert any(blocker.lower() in b.lower() for b in actual["blockers"]), \
                f"missing blocker: {blocker}"
    # Requirements + risks present
    if expected_band != "reject":
        assert actual["requirement_count"] >= 5, \
            f"only {actual['requirement_count']} requirements extracted"
    # Approval block always present
    assert "approval" in actual["package_sections_present"], \
        "human_approval_required must be present (§5.13)"
```

- [ ] **Step 3: Makefile target**

```makefile
eval: ## Run the evaluation harness against seeded fixtures (PRD §19)
	uv run python -m eval.runner.run
```

- [ ] **Step 4: First run + capture goldens (manual review)**

```bash
make eval  # may fail; review actual vs expected; tune prompts
```

For each fixture's first successful run, save `actual` to `/Volumes/CS_Stuff/govcon/eval/goldens/<slug>.json` for future drift detection.

- [ ] **Step 5: Commit**

```bash
git add eval/ Makefile
git commit -m "feat(eval): A12 eval harness with §11.1 + §5.13 assertions"
```

---

# PHASE 6 — Product UI (`/web`)

Consumes the SSE stream + REST API. Replaces the marketing-only `/landing`. Built in dependency order: API client → profile/goal entry → timeline → cards → detail → action package → approval gate.

---

### Task 6.1: B2 — API client + zod types from /schemas

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/web/src/lib/api.ts`
- Create: `/Volumes/CS_Stuff/govcon/web/src/lib/types/` — TS types (codegen target)
- Create: `/Volumes/CS_Stuff/govcon/web/scripts/codegen.mjs` — TS codegen from /schemas
- Modify: `/Volumes/CS_Stuff/govcon/web/package.json` — add `codegen` script

- [ ] **Step 1: Add codegen script**

```javascript
// web/scripts/codegen.mjs
import { compileFromFile } from "json-schema-to-typescript";
import { readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const schemasDir = "../schemas";
const outDir = "src/lib/types";
const files = readdirSync(schemasDir).filter(f => f.endsWith(".schema.json"));
for (const f of files) {
  const ts = await compileFromFile(join(schemasDir, f));
  const name = f.replace(".schema.json", "").replace(/-/g, "_");
  writeFileSync(join(outDir, `${name}.ts`), ts);
  console.log(`✓ ${name}.ts`);
}
```

```json
// web/package.json
"scripts": {
  "codegen": "node scripts/codegen.mjs"
},
"devDependencies": {
  "json-schema-to-typescript": "^15.0.0"
}
```

- [ ] **Step 2: API client**

```typescript
// web/src/lib/api.ts
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  createProfile: (body: unknown) => request("/company-profiles", { method: "POST", body: JSON.stringify(body) }),
  getProfile: (id: string) => request(`/company-profiles/${id}`),
  createRun: (body: unknown) => request("/agent-runs", { method: "POST", body: JSON.stringify(body) }),
  getRun: (id: string) => request(`/agent-runs/${id}`),
  getRunOpportunities: (id: string) => request(`/agent-runs/${id}/opportunities`),
  getOpportunity: (id: string) => request(`/opportunities/${id}`),
  getRequirements: (id: string) => request(`/opportunities/${id}/requirements`),
  getFitScore: (id: string) => request(`/opportunities/${id}/fit-score`),
  getRisks: (id: string) => request(`/opportunities/${id}/risks`),
  getActionPackage: (id: string) => request(`/action-packages/${id}`),
  resumeRun: (id: string, answer: unknown) =>
    request(`/agent-runs/${id}/resume`, { method: "POST", body: JSON.stringify({ answer }) }),
};
```

- [ ] **Step 3: Run codegen, commit**

```bash
cd web && npm install && npm run codegen
git add web/scripts/ web/src/lib/ web/package.json web/package-lock.json
git commit -m "feat(web): B2 API client + zod-codegen from /schemas"
```

---

### Task 6.2-6.3: B3 + B4 — Profile + Goal entry screens

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/web/src/app/profile/page.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/app/runs/new/page.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/ProfileForm.tsx`

- [ ] **Step 1: Profile form**

```tsx
"use client";
import { useState } from "react";
import { api } from "@/lib/api";

export default function ProfileForm() {
  const [form, setForm] = useState({
    name: "", website: "", description: "",
    capabilities: "", industry_keywords: "",
    naics_codes: "", certifications: "",
    small_business_status: true, sam_status: "registered",
    clearance_status: "none", location: "", service_area: "",
    preferred_role: "either",
  });
  // ... onChange + onSubmit posting to api.createProfile
  return <form className="space-y-4 max-w-2xl">{/* shadcn-style inputs */}</form>;
}
```

- [ ] **Step 2: Goal entry route**

`web/src/app/runs/new/page.tsx`:

```tsx
"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export default function NewRun() {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [profileId, setProfileId] = useState("");
  // ... onSubmit calls api.createRun({ profile_id: profileId, goal });
  // router.push(`/runs/${run.id}`);
  return <div>...</div>;
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/app/profile/ web/src/app/runs/ web/src/components/ProfileForm.tsx
git commit -m "feat(web): B3+B4 profile + goal entry screens"
```

---

### Task 6.4: B5a — SSE consumer hook

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/web/src/lib/useTraceStream.ts`

- [ ] **Step 1: Hook**

```typescript
"use client";
import { useEffect, useState } from "react";

export type TraceEvent =
  | { type: "run_started"; run_id: string; goal: string; ts: string }
  | { type: "run_completed"; run_id: string; status: string; summary: string; ts: string }
  | { type: "step_started"; run_id: string; step_id: string; label: string; ts: string }
  | { type: "step_completed"; run_id: string; step_id: string; status: string; ts: string }
  | { type: "tool_called"; run_id: string; step_id: string; tool: string;
      input: unknown; rationale: string; ts: string }
  | { type: "tool_returned"; run_id: string; step_id: string; tool: string;
      output: unknown; error: string | null; latency_ms: number; cost_usd: number; ts: string }
  | { type: "opportunity_ranked"; run_id: string; opportunity_id: string;
      score: number; decision: string; ts: string }
  | { type: "needs_human"; run_id: string; question: string; context: unknown; ts: string }
  | { type: "subagent_spawned"; run_id: string; agent_role: string;
      child_id: string; parent_id: string; ts: string }
  | { type: "subagent_completed"; run_id: string; child_id: string;
      status: string; ts: string };

export function useTraceStream(runId: string) {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  useEffect(() => {
    if (!runId) return;
    const base = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
    const es = new EventSource(`${base}/agent-runs/${runId}/stream`);
    const handler = (e: MessageEvent) => {
      try {
        const evt = JSON.parse(e.data) as TraceEvent;
        setEvents(prev => [...prev, evt]);
      } catch { /* ignore parse errors */ }
    };
    // Listen on each event type
    [
      "run_started", "run_completed", "step_started", "step_completed",
      "tool_called", "tool_returned", "opportunity_ranked", "needs_human",
      "subagent_spawned", "subagent_completed",
    ].forEach(t => es.addEventListener(t, handler));
    return () => es.close();
  }, [runId]);
  return events;
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/lib/useTraceStream.ts
git commit -m "feat(web): B5a SSE consumer hook (typed event union)"
```

---

### Task 6.5: B5b — Timeline UI

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/Timeline.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/app/runs/[id]/page.tsx`

- [ ] **Step 1: Timeline component**

```tsx
"use client";
import { useTraceStream, type TraceEvent } from "@/lib/useTraceStream";

export function Timeline({ runId }: { runId: string }) {
  const events = useTraceStream(runId);
  // Group by step_id; render each step with status icon + tool calls inside
  // Render subagent spawns as nested indents
  return (
    <ol className="space-y-2">
      {events.map((e, i) => (
        <li key={i} className="flex gap-3">
          <StatusDot type={e.type} />
          <div>
            <div className="text-sm font-medium">{labelFor(e)}</div>
            {"latency_ms" in e && (
              <div className="text-xs text-slate-500">
                {e.latency_ms}ms · ${e.cost_usd.toFixed(4)}
              </div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function labelFor(e: TraceEvent): string {
  switch (e.type) {
    case "run_started": return `Run started: ${e.goal}`;
    case "step_started": return e.label;
    case "tool_called": return `→ ${e.tool}`;
    case "tool_returned": return `← ${e.tool}${e.error ? ` (${e.error})` : ""}`;
    case "opportunity_ranked": return `Ranked ${e.opportunity_id}: ${e.decision} (${e.score})`;
    case "needs_human": return `⚠ ${e.question}`;
    case "subagent_spawned": return `Spawned ${e.agent_role}`;
    case "subagent_completed": return `${e.agent_role} completed`;
    case "run_completed": return `Run ${e.status}: ${e.summary}`;
    default: return e.type;
  }
}

function StatusDot({ type }: { type: string }) { /* color by type */ }
```

- [ ] **Step 2: Run page**

```tsx
import { Timeline } from "@/components/Timeline";
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">Run {id.slice(0, 8)}</h1>
      <Timeline runId={id} />
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/Timeline.tsx web/src/app/runs/[id]/
git commit -m "feat(web): B5b live SSE timeline UI"
```

---

### Task 6.6: B6 — Ranked opportunity cards

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/OpportunityCard.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/RankedList.tsx`
- Modify: `/Volumes/CS_Stuff/govcon/web/src/app/runs/[id]/page.tsx` — add ranked list

- [ ] **Step 1: Card component**

```tsx
type DecisionBand = "strong_pursue" | "pursue" | "maybe" | "reject";
const BAND_COLORS: Record<DecisionBand, string> = {
  strong_pursue: "bg-emerald-50 border-emerald-300 text-emerald-900",
  pursue: "bg-sky-50 border-sky-300 text-sky-900",
  maybe: "bg-amber-50 border-amber-300 text-amber-900",
  reject: "bg-rose-50 border-rose-300 text-rose-900",
};

export function OpportunityCard({ opp }: { opp: { id: string; title: string;
  agency: string; due_date: string; naics: string; set_aside: string;
  fit_score: number; decision: DecisionBand; top_reason: string;
  main_risk: string; }}) {
  return (
    <a href={`/opportunities/${opp.id}`}
       className={`block rounded-xl border p-4 ${BAND_COLORS[opp.decision]}`}>
      <div className="flex justify-between gap-4">
        <div>
          <div className="text-xs uppercase">{opp.agency}</div>
          <h3 className="text-lg font-semibold">{opp.title}</h3>
          <div className="text-xs mt-1">Due {opp.due_date} · NAICS {opp.naics}</div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold">{opp.fit_score}</div>
          <div className="text-xs uppercase">{opp.decision.replace("_", " ")}</div>
        </div>
      </div>
      <div className="mt-3 text-sm">✓ {opp.top_reason}</div>
      <div className="text-sm">⚠ {opp.main_risk}</div>
    </a>
  );
}
```

- [ ] **Step 2: List component fetches via api.getRunOpportunities**

- [ ] **Step 3: Commit**

```bash
git add web/src/components/OpportunityCard.tsx web/src/components/RankedList.tsx web/src/app/runs/[id]/page.tsx
git commit -m "feat(web): B6 ranked opportunity cards with decision bands"
```

---

### Task 6.7-6.9: B7a-c — Detail layout, PDF deep-link, score breakdown

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/web/src/app/opportunities/[id]/page.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/RequirementsList.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/ScoreBreakdown.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/PdfDeepLink.tsx`

- [ ] **Step 1: Detail page composes Requirements + Score + Risks + PDF link**

```tsx
export default async function OpportunityDetail({ params }) {
  const { id } = await params;
  const [opp, reqs, score, risks] = await Promise.all([
    api.getOpportunity(id), api.getRequirements(id),
    api.getFitScore(id), api.getRisks(id),
  ]);
  return (
    <main className="mx-auto max-w-5xl p-8 space-y-8">
      <header><h1>{opp.title}</h1><div>{opp.agency} · Due {opp.due_date}</div></header>
      <ScoreBreakdown score={score} />
      <RequirementsList requirements={reqs} oppId={id} />
      <RiskRegister risks={risks} />
    </main>
  );
}
```

- [ ] **Step 2: RequirementsList shows evidence_snippet + page_number → click opens PDF at page**

```tsx
export function RequirementsList({ requirements, oppId }) {
  return (
    <ul className="space-y-3">
      {requirements.map(r => (
        <li key={r.id} className="border-l-2 pl-4">
          <div className="font-medium">{r.title}</div>
          <div className="text-sm">{r.value}</div>
          {r.evidence_snippet && (
            <a href={`/opportunities/${oppId}/pdf?page=${r.page_number}`}
               className="block mt-1 text-xs italic text-slate-600">
              "{r.evidence_snippet}" — p.{r.page_number}
            </a>
          )}
          <ConfidenceBadge level={r.confidence} />
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 3: ScoreBreakdown — bar chart of 9 dimensions**

Use a simple inline-SVG horizontal bar chart (one rect per dimension). No chart library needed.

- [ ] **Step 4: PDF deep-link route — proxy to Supabase Storage signed URL**

`web/src/app/opportunities/[id]/pdf/route.ts` (App Router route handler):

```typescript
export async function GET(req: Request, { params }) {
  const { id } = await params;
  const url = new URL(req.url);
  const page = url.searchParams.get("page") ?? "1";
  // Fetch signed URL from FastAPI: GET /opportunities/{id}/pdf-url
  const signed = await api.getPdfUrl(id);
  return Response.redirect(`${signed}#page=${page}`, 302);
}
```

(This requires adding `GET /opportunities/{id}/pdf-url` on the backend that returns a Supabase Storage signed URL — small backend addition.)

- [ ] **Step 5: Commit**

```bash
git add web/src/app/opportunities/ web/src/components/RequirementsList.tsx \
        web/src/components/ScoreBreakdown.tsx web/src/components/PdfDeepLink.tsx
git commit -m "feat(web): B7 opportunity detail + requirements + PDF deep-link + score chart"
```

---

### Task 6.10-6.13: B8a-d — Action package screens

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/web/src/app/action-packages/[id]/page.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/ExecutiveBrief.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/ComplianceMatrix.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/RiskRegister.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/ProposalChecklist.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/Timeline.tsx` (action-package timeline; rename above to RunTimeline)
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/PartnerSuggestions.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/OutreachDraft.tsx`
- Create: `/Volumes/CS_Stuff/govcon/web/src/components/ApprovalGate.tsx`

- [ ] **Step 1: Action package page composes all sub-components**

```tsx
export default async function ActionPackagePage({ params }) {
  const { id } = await params;
  const pkg = await api.getActionPackage(id);
  return (
    <main className="mx-auto max-w-4xl p-8 space-y-10">
      <ApprovalGate items={pkg.human_approval_required} />
      <ExecutiveBrief summary={pkg.executive_summary} decision={pkg.decision}
                     fitScore={pkg.fit_score} rationale={pkg.fit_rationale} />
      <ComplianceMatrix rows={pkg.compliance_matrix} />
      <RiskRegister risks={pkg.risk_register} />
      <ProposalChecklist items={pkg.proposal_checklist} />
      <ActionTimeline items={pkg.timeline} />
      {pkg.partner_suggestions.length > 0 && <PartnerSuggestions items={pkg.partner_suggestions} />}
      {pkg.outreach_draft && <OutreachDraft draft={pkg.outreach_draft} />}
    </main>
  );
}
```

- [ ] **Step 2: ApprovalGate — sticky-top yellow banner**

```tsx
export function ApprovalGate({ items }: { items: string[] }) {
  return (
    <div className="sticky top-0 z-10 rounded-md border border-amber-400 bg-amber-50 p-4">
      <div className="font-semibold text-amber-900">Human approval required</div>
      <ul className="mt-2 list-disc pl-5 text-sm text-amber-900">
        {items.map((it, i) => <li key={i}>{it}</li>)}
      </ul>
      <div className="mt-3 flex gap-2">
        <button className="rounded bg-amber-600 px-3 py-1.5 text-white text-sm">Mark reviewed</button>
        <button className="rounded border border-amber-600 px-3 py-1.5 text-amber-900 text-sm">Copy outreach draft</button>
        <button className="rounded border border-amber-600 px-3 py-1.5 text-amber-900 text-sm">Export package</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: ComplianceMatrix — table with status badges**

```tsx
const STATUS_COLOR = {
  met: "bg-emerald-100 text-emerald-900",
  missing: "bg-rose-100 text-rose-900",
  unclear: "bg-amber-100 text-amber-900",
  not_applicable: "bg-slate-100 text-slate-700",
};
export function ComplianceMatrix({ rows }) {
  return (
    <table className="w-full text-sm">
      <thead><tr><th>Requirement</th><th>Status</th><th>Evidence</th>
        <th>Next action</th><th>Owner</th></tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td>{r.requirement}</td>
            <td><span className={`px-2 py-0.5 rounded ${STATUS_COLOR[r.status]}`}>{r.status}</span></td>
            <td className="text-xs italic">{r.evidence}</td>
            <td>{r.next_action}</td><td>{r.owner}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: Other components follow same shape (RiskRegister, ProposalChecklist, etc.)**

- [ ] **Step 5: Smoke-test the full flow**

```bash
# Backend running:
make dev
# In another terminal:
npm -w web run dev
# Navigate browser through: /profile → /runs/new → /runs/{id} → /opportunities/{id} → /action-packages/{id}
```

- [ ] **Step 6: Commit**

```bash
git add web/src/components/ web/src/app/action-packages/
git commit -m "feat(web): B8 action package screens (brief, matrix, register, checklist, gate)"
```

---

# PHASE 7 — Production Hardening

Stuff you want before showing this to real users.

---

### Task 7.1: Repository transaction boundaries

**Why:** Multi-step writes (e.g., a single skill writing N requirements + 1 fit_score + N risks) currently auto-commit per call. A failure midway leaves partial data. Wrap related writes in a transaction.

**Files:**
- Modify: `/Volumes/CS_Stuff/govcon/api/repositories/*.py` — drop auto-commits, add `async with session.begin()` at handler boundaries

- [ ] **Step 1: Remove `await self._session.commit()` from each repo create/update method**

The session lifecycle is owned by the request via `deps.py:get_session()`. Move the commit to a single `async with session.begin()` block in the route handler or the agent runner.

- [ ] **Step 2: Update tests where commit was implicit**

- [ ] **Step 3: Commit**

```bash
git add api/repositories/ api/routes/ api/tests/
git commit -m "refactor(repo): move commit boundaries to handler/runner level"
```

---

### Task 7.2: Anthropic retry/backoff

**Files:**
- Modify: `/Volumes/CS_Stuff/govcon/api/llm.py` — wrap `messages.create` with exponential backoff on 429 + 5xx

- [ ] **Step 1: Add tenacity dep**

```toml
"tenacity>=9.0",
```

- [ ] **Step 2: Decorate the LLM call**

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import anthropic

@retry(
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIError)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    reraise=True,
)
async def _call_with_retry(self, **kwargs):
    return await self._client.messages.create(**kwargs)
```

- [ ] **Step 3: Test (mock raising RateLimitError twice then succeeding)**

- [ ] **Step 4: Commit**

```bash
git add api/llm.py pyproject.toml uv.lock api/tests/test_llm.py
git commit -m "feat(llm): exponential backoff retry on Anthropic 429/5xx (4 attempts)"
```

---

### Task 7.3: Structured logging

**Files:**
- Modify: `/Volumes/CS_Stuff/govcon/api/main.py` — configure `structlog`
- Modify: `/Volumes/CS_Stuff/govcon/pyproject.toml` — add structlog dep

- [ ] **Step 1: Wire structlog**

```python
# api/main.py
import structlog, logging, sys
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
)
log = structlog.get_logger()
```

- [ ] **Step 2: Replace print/logging.info calls in skills + bridge**

- [ ] **Step 3: Commit**

```bash
git add api/main.py api/agent/ api/skills/ pyproject.toml uv.lock
git commit -m "feat(logging): structlog with JSON renderer + contextvars"
```

---

### Task 7.4: Run budget enforcement

**Why:** Hermes claims to enforce `max_steps` / `max_cost_usd` / `max_seconds`, but verify. Add an explicit guard in the runner that emits `run_completed` with `status=partial` when any budget is exhausted.

**Files:**
- Modify: `/Volumes/CS_Stuff/govcon/api/agent/hermes_runner.py`
- Test: `/Volumes/CS_Stuff/govcon/api/tests/test_hermes_runner.py`

- [ ] **Step 1: Wrap agent.run with asyncio.wait_for(timeout=settings.run_budget_seconds)**

```python
import asyncio
try:
    await asyncio.wait_for(agent.run(...), timeout=settings.run_budget_seconds)
except asyncio.TimeoutError:
    await deps["redis"].publish(channel, json.dumps({
        "type": "run_completed", "run_id": str(run_id),
        "status": "partial", "summary": "Wall-clock budget exceeded.",
        "ts": datetime.utcnow().isoformat() + "Z",
    }))
```

- [ ] **Step 2: Track cumulative cost via tool_returned events; abort when exceeded**

- [ ] **Step 3: Test with a fake agent that runs forever; assert run_completed/partial**

- [ ] **Step 4: Commit**

```bash
git add api/agent/hermes_runner.py api/tests/test_hermes_runner.py
git commit -m "feat(agent): enforce wall-clock + cost budgets, emit partial completion"
```

---

### Task 7.5: §11.1 enforcement audit

**Why:** The rule is enforced inside `score_fit` — but Hermes might call score_fit multiple times, or skip it for some reason. Add a final gate in the runner: before persisting any action_package with `decision != reject`, re-check that none of the persisted requirements are eligibility blockers.

**Files:**
- Modify: `/Volumes/CS_Stuff/govcon/api/agent/hermes_runner.py` — add post-run audit

- [ ] **Step 1: Audit function**

```python
async def _audit_eligibility(run_id, opp_repo, action_pkg):
    if action_pkg.decision == "reject":
        return  # already rejected
    requirements = await opp_repo.list_requirements(action_pkg.opportunity_id)
    blockers = _check_eligibility_short_circuit(
        company_profile=action_pkg.company_profile,
        requirements=[r.__dict__ for r in requirements],
    )
    if blockers:
        # CRITICAL: agent failed to enforce §11.1 — override
        log.error("eligibility_audit_override", blockers=blockers, run_id=run_id)
        action_pkg.decision = "reject"
        action_pkg.executive_summary = (
            f"OVERRIDE: §11.1 audit found eligibility blockers: {blockers}"
        )
```

- [ ] **Step 2: Eval-harness assertion (Phase 5) catches this regression**

- [ ] **Step 3: Commit**

```bash
git add api/agent/hermes_runner.py
git commit -m "feat(agent): post-run §11.1 audit override (defense-in-depth)"
```

---

### Task 7.6: SAM.gov fallback chain

**Why:** PRD §5.4 fallback: live → cached → seeded. Implement the cache layer.

**Files:**
- Create: `/Volumes/CS_Stuff/govcon/api/skills/search_sam/cache.py`
- Modify: `/Volumes/CS_Stuff/govcon/api/skills/search_sam/skill.py` — wrap with cache lookup before live call

- [ ] **Step 1: Postgres-backed cache table**

Migration `0004_sam_cache.py`:

```python
def upgrade():
    op.create_table("sam_cache",
        sa.Column("id", sa.UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("query_key", sa.String, unique=True, index=True),  # hash of params
        sa.Column("results", sa.JSON, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
```

- [ ] **Step 2: SearchSamSkill.run logic**

```
1. Compute query_key from input params.
2. If cache hit and fetched_at < 24h ago: return cached, mark NOT degraded.
3. Else call live SAM.
4. On success: write to cache.
5. On 429/5xx: return cache if any (degraded=False, age noted), else degraded=True with empty.
6. Caller (Hermes Capture Lead) checks .degraded — if True AND results empty, fall back to load_seeded_opportunities.
```

- [ ] **Step 3: Test cache-hit, cache-miss, stale-cache-on-error paths**

- [ ] **Step 4: Commit**

```bash
git add api/skills/search_sam/ api/migrations/versions/0004_*.py api/tests/test_search_sam.py
git commit -m "feat(skills): SAM cache layer (live → cached → seeded fallback)"
```

---

# Self-Review

Spec coverage check, run against PRD §5 (features), §4.5 (agent architecture), §10 (output schemas), §11.1 (eligibility), §13.1 (demo script), §19 (eval), §7 (stack):

- ✓ §5.1 Profile input — Task 6.2 (form), Task 0.1 (POST already exists)
- ✓ §5.2 Goal input — Task 6.3
- ✓ §5.3 Run timeline — Task 6.5
- ✓ §5.4 Opportunity loader — Task 1.5 (load_seeded), Task 3.1 (search_sam), Task 7.6 (cache)
- ✓ §5.5 Document parsing — already done (parse_pdf A4)
- ✓ §5.6 Requirement extraction — already done (extract_requirements A5)
- ✓ §5.7 Fit scoring — Task 2.1, 2.2
- ✓ §5.8 Risk detection — Task 2.3, 2.4
- ✓ §5.9 Ranking — Task 3.4 + Task 6.6
- ✓ §5.10 Detail view — Task 6.7-6.9
- ✓ §5.11 Action package — Task 2.5, 2.6 + Task 6.10-6.13
- ✓ §5.12 Partner suggestion — included in action package full mode + Task 6.10-6.13 component
- ✓ §5.13 Approval gate — Task 6.10-6.13 (ApprovalGate component) + forced default in skill
- ✓ §4.5 Planner loop — Task 4.2 (hermes_runner)
- ✓ §4.5 Tool registry — Task 4.2 (skill_registry)
- ✓ §4.5 Decision policy / error recovery — Task 7.4 (budget) + 7.6 (SAM fallback) + 4.6 (human review)
- ✓ §4.5 Observability — Task 4.3 (bridge) + Task 7.3 (structured logs)
- ✓ §10 Structured outputs — all schemas already locked; codegen via Task 6.1
- ✓ §11.1 Eligibility conservatism — Task 2.1+2.2 (skill), Task 5.1 (eval), Task 7.5 (audit override)
- ✓ §13.1 Demo script — entire Phase 1 + 4 + 6 enables it
- ✓ §19 Eval harness — Phase 5
- ✓ §7.1 Frontend — Phase 6
- ✓ §7.2 Backend — Phases 0, 2, 3, 4, 7
- ✓ §7.3 Agent layer — Phase 4
- ✓ §7.5 Storage — already wired
- ✓ §7.6 Deploy — already done in repo

**Placeholder scan:** all "..." in code blocks are intentional (object spread / shorthand for fields not relevant to the example). Phase 4 has the only true placeholders — input_schema/output_schema for each registered skill — fix by spelling out one example per skill type when implementing Task 4.2.

**Type consistency:**
- `ScoreFitOutput.decision` is a Literal — used consistently in Task 2.2 / 5.1 / 6.6.
- `RiskFlag.severity` is consistent across Task 2.4 (`critical_blocker`) and Task 6.10-13 component.
- `TraceEvent` discriminated union in Task 6.4 covers all 8 base + 2 subagent types from Task 4.3.
- `mode: "full" | "reject_summary"` consistent in Task 2.6 + 4.4 (skill manifest).

**One inconsistency to note (fixed):** Task 6.5 introduces `Timeline.tsx` for the run timeline, but Task 6.10-6.13 also wants a `Timeline` for the action-package timeline. **Renamed action-package one to `ActionTimeline.tsx` in Task 6.10**.

---

**Estimated total runway:** 19-24 working days for one engineer; 11-14 if Track A and Track B run parallel after Phase 0.

**Critical-path tasks** (everything blocks on these):
- Task 4.1 (Hermes spike) — biggest unknown
- Task 1.1-1.4 (fixtures) — unblock eval harness + demo
- Task 2.2 (score_fit §11.1) — unblocks A8 reject mode + eval reject assertion
