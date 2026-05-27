---
name: govcapture-infrastructure
description: "Build and verify GovCapture's real data rails: SAM.gov search, fixture capture, PDF download/parsing, semantic embeddings, autonomous heartbeat, Supabase storage, and proof-first demo readiness."
version: 1.2.0
author: Hermes Agent
metadata:
  hermes:
    tags: [govcapture, sam-gov, pdf, fixtures, infrastructure, embeddings, heartbeat, supabase, storage]
    related_skills: [discover_opportunities, analyze_opportunity_e2e, test-driven-development]
---

# GovCapture Infrastructure

Use this when the task is to make GovCapture real, not pretty: government opportunity data, attachments, PDF text, fixtures, semantic matching, autonomous polling, Supabase storage, and the first deterministic rail into extraction/scoring.

## Operating posture

- Infrastructure before UI: prove `SAM.gov → opportunity JSON → attachment PDF → parsed page chunks → embedding vectors → ranked matches` before polishing screens.
- Proof, not description: report concrete outputs (`4,616 records found`, `4 pages parsed`, `13,905 chars`, `0.87 cosine match`, `bid memo ready`) instead of explaining mechanisms.
- Never print API keys back. Store secrets in `.env` with `0600` and keep `.env` gitignored.
- **Credential hygiene**: the GovCon `.env` is at `/root/govcon/.env`. Check it FIRST before searching the filesystem. It contains SAM_API_KEY, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY, and all provider keys. When the user says "use GovCon" or "reach Supabase," read this file — do not scan the entire filesystem while the user watches.

## Procedure

1. **Wire secrets safely**
   - Save `SAM_API_KEY` and `OPENAI_API_KEY` to project `.env` and Hermes `.env` if needed.
   - Set mode `0600`.
   - Verify presence without echoing the value.

2. **Prove live SAM.gov search (Opportunities)**
   - Query `https://api.sam.gov/opportunities/v2/search`.
   - Required params: `api_key`, `keyword`, `postedFrom`, `postedTo`, `ptype`, `limit`, `offset`.
   - Dates must be `MM/DD/YYYY`.
   - Use `ptype=o` for active solicitations/opportunities.
   - Use `ptype=a` for SAM.gov award notices (thin — limited dollar data, no subcontract history). For rich award data use the Contract Awards API below.
   - Normalize records into internal opportunity fields: notice ID, title, agency, solicitation number, due date, award date/amount/awardee when present, NAICS, set-aside, place of performance, source URL, attachments, raw payload.

2b. **SAM.gov Contract Awards API (rich historical awards)**
   - Endpoint: GET `https://api.sam.gov/contract-awards/v1/search?api_key=KEY&limit=N`
   - **REQUIRED HEADER**: `User-Agent: Mozilla/5.0` — requests WITHOUT this header hang and return empty.
   - **SHELL SAFETY**: Always assign URL to a variable before curling — `&` in query params gets interpreted as shell background operator. Use: `URL="..."` then `curl "$URL"`.
   - **URL ENCODING**: Square brackets in range params MUST be URL-encoded: `[` → `%5B`, `]` → `%5D`. Example: `lastModifiedDate=%5B01/01/2026,05/12/2026%5D`. Unencoded brackets cause empty responses.
   - This is separate from the Opportunities API — dedicated to FPDS contract data (Definitive Contracts, Task Orders, GWACs, BPAs, IDVs, FSS, Purchase Orders, BPA Calls, OTs).
   - Two tiers:
     - **Revealed** (any account): civilian contracts + DoD contracts signed ≥ 90 days ago.
     - **Unrevealed** (federal/DoD accounts only): all revealed + recent DoD (< 90 days) + parent company UEI/name.
   - **Working parameters** (confirmed May 2026):
     - `limit=N` — records per page (default 10, max 100)
     - `lastModifiedDate=%5BMM/DD/YYYY,MM/DD/YYYY%5D` — date range filter ✓
     - `dollarsObligated=%5BMIN,MAX%5D` — dollar range filter (requires explicit upper bound, e.g. `99999999999`) ✓
     - `includeSections=X,Y,Z` — narrows which TOP-LEVEL sections are returned (contractId, coreData, awardDetails). awardeeData is NESTED inside awardDetails by default — NOT a top-level section.
     - `modificationNumber=0` — base contracts only
     - `fiscalYear=YYYY` — fiscal year filter
     - `typeOfSetAsideCode=SBA` — set-aside filter
   - **NOT working**: `sort` param (returns error: "does not exist"), `offset`/`page` pagination (returns 400 — use client-side sorting/pagination from larger batches).
   - Logical operators: `&` (AND), `~` (OR), `!` (NOT).
   - **Response structure** (default, no includeSections):
     - `awardSummary[]` (NOT `awards`) — array of award objects
     - `awardSummary[].awardDetails.awardeeData.awardeeHeader.awardeeName` — vendor name
     - `awardSummary[].awardDetails.dollars.actionObligation` — dollar amount
     - `awardSummary[].coreData.competitionInformation.numberOfOffersReceived` — offer count
     - `awardSummary[].coreData.productOrServiceInformation.descriptionOfContractRequirement` — description
     - `awardSummary[].coreData.federalOrganization.contractingInformation.contractingSubtier.name` — agency name
     - `totalRecords` (NOT `totalCount`) — total matching count
   - Sync mode: 10-100 records/page, max 400,000 records via pagination.
   - Async bulk extract: add `format=json` or `format=csv` → get download URL with token → up to 1,000,000 records.
   - Rate limits: 10/day (non-fed no-role), 1,000/day (non-fed with role / federal personal / non-fed system), 10,000/day (federal system).
   - Docs: https://open.gsa.gov/api/contract-awards/
   - OpenAPI spec: https://open.gsa.gov/api/contract-awards/v1/openapi.yaml

3. **Capture a deterministic fixture immediately**
   - Pick one live opportunity with `resourceLinks`.
   - Download attachments until one parseable PDF is found.
   - Parse filename from `Content-Disposition` when present.
   - Save:
     - `fixtures/<slug>/opportunity.json`
     - `fixtures/<slug>/attachments/*.pdf`
     - optional `fixtures/<slug>/parsed-preview.json`

4. **Parse PDFs locally**
   - Use `pypdf` for MVP; no OCR.
   - Return 1-indexed physical PDF page numbers.
   - Mark `unparseable=true` and return empty chunks when total extracted text is below threshold.
   - Split very long pages by paragraph while preserving page number.

5. **Embed opportunities for semantic matching**
   - Use `text-embedding-3-small` (1536 dims, $0.02/1M tokens). Default for GovCon. Only bump to `text-embedding-3-large` (3072 dims, $0.13/1M) if small produces bad matches.
   - Cost model: embed each document **once**, cache the vector. Cosine similarity lookups are local math — zero API cost. ~$0.20/month for 10k new contracts.
   - Pipeline: SAM.gov → opportunity JSON → PDF parse → embed description → store vector. Company profile → embed capabilities → store vector → cosine similarity → ranked matches.
   - Storage: SQLite + JSON array for MVP (no new infra). GBrain (`/root/gbrain`, v0.30.2) for future hybrid RAG — cloned but not wired, requires `bun` + `gbrain init` + pgvector.
   - See `references/openai-embeddings.md` for full API pattern and model comparison.

6. **Test first**
   - Write tests for query construction and normalization before implementing the SAM adapter.
   - Write tests for parseable and blank/image-only PDFs before implementing the parser.
   - Write tests for embedding generation and cosine similarity before wiring the matching layer.
   - Use environment isolation for missing-key tests: `monkeypatch.delenv(...)` plus `monkeypatch.chdir(tmp_path)`.

## Supabase Storage

GovCapture assets (images, video, audio) live in Supabase Storage on the Persona project (`vvyxjdoenjujkxwbnzyl.supabase.co`). The service role key is `SUPABASE_SERVICE_ROLE_KEY` in `/root/govcon/.env`.

### Buckets

| Bucket | Public | Contents |
|---|---|---|
| `michaela-images` | yes | Profile/hero/scene images |
| `michaela-video` | yes | Intro/veo/grok clips |
| `michaela-audio` | yes | Voice lines and music |
| `persona-assets` | yes | Persona profile images |
| `govcapture-attachments` | no | Empty (returned to owner) |

Base URL pattern: `https://vvyxjdoenjujkxwbnzyl.supabase.co/storage/v1/object/public/{bucket}/{path}`

### REST API quick reference

Authentication uses `apikey` + `Authorization: Bearer {key}` headers with the service role key.

- **Create bucket**: `POST /storage/v1/bucket` — body `{"name": "...", "public": true}`
- **Upload**: `POST /storage/v1/object/{bucket}/{path}` — raw bytes, header `x-upsert: true`, set `Content-Type` to the file's MIME type
- **List**: `POST /storage/v1/object/list/{bucket}` — body `{"prefix": "folder/", "limit": 100}`
- **Delete object**: `DELETE /storage/v1/object/{bucket}/{fullPath}`
- **Delete bucket**: `DELETE /storage/v1/bucket/{bucketId}` — fails 409 if not empty

### ⚠️ CRITICAL PITFALL: Prefix stripping on list

The list API **strips the prefix from returned object names**. When you list with `prefix: "images/"`, objects return as `name: "hero.png"` — NOT `"images/hero.png"`. But **DELETE requires the full path**. You MUST prepend the prefix:

```python
# WRONG — returns 404 "Object not found" for every file
for obj in list_objects(prefix="images/"):
    delete(f"{bucket}/{obj['name']}")  # tries to delete "bucket/hero.png"
                                         # but the real path is "bucket/images/hero.png"

# RIGHT
for obj in list_objects(prefix="images/"):
    delete(f"{bucket}{prefix}{obj['name']}")  # deletes "bucket/images/hero.png"
```

This is NOT documented by Supabase. The list response gives zero indication that the prefix was stripped — names look like bare filenames. This caused a full session of 400 errors before the pattern was identified. Always test a single delete first when bulk-cleaning a bucket.

### Python helper

```python
import urllib.request, json

def supabase_api(url, key, method='GET', body=None):
    headers = {'apikey': key, 'Authorization': f'Bearer {key}'}
    if body:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode()
    else:
        data = None
    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
```

## Autonomous Operations (Heartbeat)

The data rail is manual by default. The autonomous layer polls SAM on a schedule and surfaces findings without being asked.

### Heartbeat pattern

1. **Cron job** fires on a schedule (every 6–12 hours for active solicitations)
2. **Poll SAM** with a broad keyword + recent date window (`postedFrom=2d ago`)
3. **Diff against stored opportunities** — only surface new notice IDs
4. **Report**: "3 new opportunities, 2 worth looking at" with titles, agencies, deadlines, and one-line verdicts

### Cron setup via Hermes

```
cronjob create --name "govcapture-heartbeat" --schedule "6h" --deliver origin \
  --prompt "Load govcapture-infrastructure. Poll SAM.gov for new VA/facilities opportunities
  posted in the last 24h. Diff against stored fixtures. Report new findings with
  title, agency, due date, and a one-line verdict."
```

### Verification

- Create a 1-minute smoke test cron: `--schedule "1m" --repeat 1` with a narrow SAM query
- Confirm it fires, queries SAM, and delivers results to the chat
- Once confirmed, promote to the real 6h schedule

## Quick Reference: Which Endpoint For What

**Use this first.** Match your goal to the right endpoint before writing any curl.

| Goal | Endpoint | Method | Why |
|------|----------|--------|-----|
| Active solicitations to bid on | `opportunities/v2/search?ptype=o` | GET | Full titles, descriptions, due dates, attachments |
| Award notices (thin) | `opportunities/v2/search?ptype=a` | GET | Official notice of award — limited data, descriptions behind noticeid URLs |
| Rich award data + descriptions | USASpending `search/spending_by_award/` | POST | Actual dollars, full descriptions, NAICS, agency slugs |
| Historical contract detail (FPDS) | `contract-awards/v1/search` | GET | FPDS records, but THIN for non-fed accounts (no desc, no PSC, no NAICS) |
| Bulk daily SAM dump | Bulk CSV via Playwright | Script | 78k rows, bypasses ToS gate |

**SAM Opportunities API quirks:**
- `ptype=a` **ignores** the `keyword` parameter — returns unfiltered recent awards
- Award notice descriptions are behind `noticedesc?noticeid=...` URLs, not inline
- Response envelope: check BOTH `opportunitiesData` AND `_embedded.opportunities`
- Total count field: `totalRecords` (not `totalCount`)

**SAM Contract Awards API quirks:**
- Non-fed accounts get sparse data — `descriptionOfContractRequirement`, `productOrServiceCode`, `naicsCode`, `numberOfOffersReceived` all return null/empty
- For rich narrative data, use USASpending instead
- REQ'D: `User-Agent: Mozilla/5.0` header, URL-encoded brackets, shell var before curl

**USASpending quick curl:**
```bash
curl -s -X POST "https://api.usaspending.gov/api/v2/search/spending_by_award/" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "award_type_codes": ["A","B","C","D"],
      "time_period": [{"start_date": "2026-04-15", "end_date": "2026-05-12"}]
    },
    "fields": ["Award ID","Recipient Name","Award Amount","Description","Awarding Agency","NAICS Code","Action Date"],
    "limit": 5,
    "order": "desc",
    "sort": "Award Amount",
    "subawards": false
  }'
```
- Response envelope: `results[]` array, `page_metadata.hasNext` for pagination
- Award amount filter (if needed): add `"award_amounts": [{"lower": 1000000}]` to filters — field names may vary by API version; test first

## Known-good proof point

See `references/sam-gov-live-fixture-workflow.md` for the live fixture captured during the initial infra sprint.

## Pitfalls

- **Live API success without fixture capture.** This still fails demos. Capture the fixture while the live result is available.
- **Credential leakage in tests/logs.** Test query construction with fake keys and never log full URLs containing `api_key`.
- **Absolute `.env` fallback in production code.** Prefer env var or project-local `.env`; absolute developer paths make tests leaky and code non-portable.
- **Committing secrets but not PDFs.** Correct policy is the inverse: never commit `.env`; do commit fixture PDFs as content.
- **Jumping to LLM extraction before parser proof.** If PDF chunks are empty/noisy, requirement extraction will hallucinate or degrade.
- **Embedding without caching.** Don't re-embed the same document on every query. Store vectors once and reuse. Re-embed only when the source text changes.
- **Heartbeat without diffing.** If the cron re-reports every opportunity it finds (not just new ones), it becomes noise. Always diff against stored notice IDs.
- **Supabase Storage list API strips prefixes from returned names.** Object names from `POST /object/list/` with `prefix: "images/"` return as `"hero.png"`, not `"images/hero.png"`. DELETE requires the full path. Always prepend the prefix when constructing delete URLs.
- **Filesystem-wide credential scans are wasteful.** The GovCon `.env` is at `/root/govcon/.env`. When told to reach Supabase or use GovCon credentials, read that file first. Don't search the entire filesystem and report "no creds found" while the user watches.

## Verification

- Live SAM.gov query returns at least one opportunity for the target goal or falls back to seeded fixtures with a degraded status.
- At least one fixture has `opportunity.json` and a parseable PDF attachment.
- `parse_pdf` returns non-empty chunks with valid page numbers.
- OpenAI embedding call returns a 1536-dim vector for a test description.
- A 1-minute heartbeat smoke test fires, queries SAM, and delivers results.
- Tests cover SAM query construction, normalization, missing key behavior, parseable PDF, blank/image-only PDF, embedding generation, and cosine similarity.
- Supabase Storage: buckets exist, objects upload/list/delete via REST API, prefix stripped from list names.