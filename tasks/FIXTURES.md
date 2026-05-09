# Fixtures

Fixtures are the demo-stable backbone of the entire product. The §13.1 demo runs against them. The §19 eval harness asserts against them. The agent's recovery paths are tested against them.

**Owner:** Track B authors content (`opportunity.json`, attachment PDFs, `expected.json`). Track A consumes them in `load_seeded_opportunities` and the eval runner. The `parse_pdf` and `extract_requirements` tools are tested against `/fixtures/_template/` from day 1 so author and consumer stay aligned.

---

## 1. Fixture set

Per PRD §5.4 + §19.

| Slug | Decision band | Purpose | Owner | Tasks |
|------|---------------|---------|-------|-------|
| `strong-pursue` | 85–100 | Demonstrates green-light path; full action package; all rubric dimensions strong | B | B9 |
| `maybe-needs-partner` | 55–69 | Demonstrates partner suggestion (§5.12); past-performance or capability gap | B | B10 |
| `reject` | 0–54 | Demonstrates §11.1 eligibility short-circuit; hard blocker (clearance or set-aside) | B | B11 |
| `adversarial-image-pdf` | n/a (recovery) | Image-only PDF; demonstrates §4.5 recovery; not in normal demo flow | B | B12 |

The first three are the **demo set**. All three run during §13.1. The fourth is the **recovery set**, exercised by the eval harness (§19) and not normally shown on stage.

---

## 2. Per-fixture spec

### 2.1 `strong-pursue`

**Setup:** A small-business set-aside cybersecurity service contract that aligns with the demo company's profile (Texas cybersecurity firm, NAICS 541512, CMMC L2, 12 employees).

**`opportunity.json` fields:**
- `title`: e.g., "Cybersecurity Assessment Services for Federal Agency X"
- `agency`: realistic civilian agency
- `solicitation_number`: synthetic but valid-looking (e.g., `47QFCA-26-R-0001`)
- `naics`: `541512` (matches profile)
- `set_aside`: `Total Small Business Set-Aside`
- `due_date`: ≥30 days from a fixed reference date (the demo "today")
- `place_of_performance`: Texas
- `description`: 2–3 paragraphs, realistic procurement language
- `attachments`: `["solicitation.pdf"]`

**`attachments/solicitation.pdf` content (1–2 pages, text-extractable):**
- Solicitation header (number, agency, deadline, NAICS, set-aside)
- Submission instructions (proposal due, format, contact)
- Scope of work (cybersecurity assessment activities aligning with profile capabilities)
- Required documents (past performance, technical approach, pricing)
- Evaluation criteria (technical 60%, price 40%)
- Insurance: standard commercial general liability (achievable)
- Period of performance: 12 months base + options
- No clearance required

**`expected.json` (golden):**
```json
{
  "extracted_requirements": {
    "min_count": 8,
    "required_titles": [
      "Submission deadline",
      "NAICS code 541512",
      "Total Small Business set-aside",
      "Past performance",
      "Technical approach",
      "Pricing/cost proposal",
      "Period of performance",
      "General liability insurance"
    ],
    "evidence_required_for_confidence": ["high", "medium"]
  },
  "fit_score": {
    "decision": "strong_pursue",
    "min_total": 80,
    "max_total": 100,
    "must_not_have_critical_blockers": true
  },
  "risks": {
    "critical_count": 0,
    "expected_categories": []
  },
  "action_package": {
    "all_sections_present": true,
    "partner_suggestions_count": 0
  }
}
```

### 2.2 `maybe-needs-partner`

**Setup:** Relevant scope but a past-performance threshold the demo company can't meet alone (e.g., requires "$10M+ in similar prior contracts" — demo company has $1.5M).

**`opportunity.json`:**
- Same agency style; NAICS aligned; set-aside compatible
- `due_date`: 21 days out (tighter, but feasible with partner)

**Attachment:**
- Most of strong-pursue, plus:
  - Past performance section requiring "minimum $10M aggregate value across similar contracts in the last 5 years"
  - OR a niche capability requirement the demo company doesn't have (e.g., "must hold CMMC Level 3" — demo has L2)

**`expected.json`:**
```json
{
  "extracted_requirements": {
    "required_titles": [
      "Past performance threshold ($10M minimum)",
      "..."
    ]
  },
  "fit_score": {
    "decision": "maybe",
    "min_total": 55,
    "max_total": 69,
    "must_have_weakness": "past_performance"
  },
  "risks": {
    "expected_categories": ["past_performance_weakness"],
    "critical_count": 0
  },
  "action_package": {
    "partner_suggestions_count_min": 1,
    "partner_types_include_any_of": ["past_performance_partner"]
  }
}
```

### 2.3 `reject`

**Setup:** Hard eligibility blocker that the §11.1 short-circuit must catch. Pick ONE:

- **Option A (preferred):** Requires Secret clearance. Demo company has none. Eligibility-uncertainty case → score 0, critical blocker, decision = reject.
- **Option B:** 8(a) set-aside. Demo company is not 8(a) certified.

Use Option A as the primary so the demo shows a clearance blocker (more visceral on stage). Option B can be a stretch second reject fixture if time permits.

**`opportunity.json`:**
- NAICS may even align with capability — important for the demo, because the §11.1 rule should reject *despite* strong capability match.
- `set_aside`: clearly labeled if applicable.

**Attachment:**
- Solicitation explicitly requires "active Secret clearance for all key personnel" (Option A) or "8(a) certified small business" (Option B).
- Otherwise resembles strong-pursue (so capability/NAICS would otherwise score well).

**`expected.json`:**
```json
{
  "extracted_requirements": {
    "required_titles": [
      "Secret clearance required for key personnel",
      "..."
    ],
    "must_have_blocker_flag": true
  },
  "fit_score": {
    "decision": "reject",
    "max_total": 54,
    "must_have_critical_blocker": true,
    "eligibility_score_must_be_zero": true
  },
  "risks": {
    "critical_count_min": 1,
    "expected_categories": ["clearance_required_but_unavailable"]
  },
  "action_package": {
    "decision_field_must_equal": "reject"
  }
}
```

This fixture is the §11.1 enforcement test. The eval harness asserts that capability strengths do NOT override the eligibility blocker.

### 2.4 `adversarial-image-pdf`

**Setup:** Same as strong-pursue but the attachment is an image-only PDF (rasterized) so `parse_pdf` cannot extract text via pypdf.

**Attachment:**
- Convert a real-looking solicitation page to image (e.g., screenshot → PDF) so `pypdf.extract_text` returns empty.

**`expected.json`:**
```json
{
  "parse_pdf": {
    "must_return_unparseable": true
  },
  "agent_run": {
    "must_emit_event": "needs_human OR step_completed.status == 'degraded'",
    "must_not_crash": true
  }
}
```

This fixture is consumed only by the eval harness, not by the demo flow. It enforces PRD §4.5 recovery ("PDF unparseable → mark, surface, continue").

---

## 3. Authoring guidelines (joint, locked in P0.4)

- **PDFs are text-extractable** for the 3 demo fixtures. Use a tool that produces a real text layer (e.g., LibreOffice export, `pandoc`, `weasyprint`). Don't print-to-PDF from an image source.
- **Length:** 1–2 pages per fixture. Long enough to have something to extract; short enough that LLM cost stays well under $0.50/run.
- **Realism:** procurement-style language, real-sounding section headers ("Section L — Instructions to Offerors", "Section M — Evaluation Criteria"), real-looking solicitation numbers. Don't use parody language.
- **Page references:** at least one important requirement per fixture should be on page 2 (not page 1) so the evidence-snippet → source-page deep-link UX is exercised.
- **Demo company:** all three fixtures are scored against the SAME demo company (B13). Tune fixture content so the company hits each band by design.
- **No real PII or real procurement data.** Synthetic only. Realistic but invented.

---

## 4. Demo company profile (B13)

Authored by B alongside the fixtures. Lives at `/fixtures/_demo-company/profile.json`.

Recommended shape:

```jsonc
{
  "name": "Lone Star CyberWorks",
  "website": "https://example.com",
  "description": "Texas-based cybersecurity firm specializing in...",
  "capabilities": ["security assessments", "vulnerability management", "compliance audits", "incident response"],
  "industry_keywords": ["cybersecurity", "infosec", "compliance"],
  "location": "Austin, TX",
  "service_area": ["Texas", "Federal — civilian agencies"],
  "naics_codes": ["541512", "541519", "541611"],
  "certifications": ["CMMC Level 2"],
  "small_business_status": true,
  "sam_status": "active",
  "clearance_status": "none",
  "past_performance": [
    { "agency": "...", "contract_value_usd": 1500000, "year": 2024, "scope": "..." }
  ],
  "insurance_bonding_status": "general_liability_2m",
  "preferred_contract_size": "$500K – $2M",
  "preferred_role": "either"
}
```

This shape is what hits each fixture's expected band:

- vs. strong-pursue → strong_pursue (capability match, set-aside match, NAICS match, deadline OK)
- vs. maybe-needs-partner → maybe (capability match, but past-performance gap)
- vs. reject → reject (no clearance; §11.1 short-circuit)

If you change the company profile, re-verify all three fixtures still hit their expected bands.

---

## 5. Validation

After authoring, run:

```bash
make eval-fixture FIXTURE=strong-pursue
make eval-fixture FIXTURE=maybe-needs-partner
make eval-fixture FIXTURE=reject
make eval-fixture FIXTURE=adversarial-image-pdf
make eval  # runs all four
```

All must pass before §13.1 demo rehearsal (S5).

If a fixture fails: discuss in standup whether the issue is the fixture (B owns) or the prompt/tool (A owns). Track the diagnosis in `STANDUP.md` so we don't keep relitigating.
