# Build Plan — joint reference docs

Active development happens on `main` directly with per-feature branches. The
canonical state-of-the-repo lives at `devdocs/CURRENT_STATE.md`. This
directory is the joint reference set: contracts, agent design, fixtures,
demo script, file ownership.

---

## Layout

```
tasks/
├── README.md                  ← you are here (decision log + frozen decisions)
├── CONTRACTS.md               ← schemas, SSE shapes, env, skill registry, API surface
├── FIXTURES.md                ← fixture content spec
└── LANDING_BRIEF.md           ← landing/product framing
```

Hermes runtime context for this pack: `HERMES.md` (repo root) plus the
five tool-procedure files in `.hermes/skills/govcapture/`. Michaela's
bench/persona context lives in `/root/michealaai`, not this repo.

---

## Working surface

- FastAPI capability-pack API + GovCon tool surface
- Michaela bench integration target (`/root/michealaai`: Michaela +
  Scot/Lenny/Gabby/Lance/Happer/Roy)
- `supabase/migrations/*.sql` for schema (no Alembic)
- Next.js `/web` (product) + `/landing` (marketing) on Vercel
- Vultr VX1 hosts FastAPI + Redis + nginx natively (no Docker). The
  Michaela orchestrator runs separately.

---

## Frozen decisions

These are settled. Do not relitigate without a logged decision below.

| Area | Decision | Source |
|------|----------|--------|
| Hackathon track | Agents Track primary; optional Texas Open Data layer | PRD §17 Q9 |
| Deployment target | Vultr VX1 (16 vCPU / 64 GB / 960 GB / Ubuntu 24.04) | PRD §7.6 |
| Agent runtime | **hermes-agent** (Nous Research) belongs to the Michaela project; this repo only carries pack-local Hermes context + tool procedures for isolated testing | `HERMES.md`, `devdocs/MICHAELA_SYSTEM_MODEL.md` |
| Agent identities | Michaela / Scot / Lenny / Gabby / Lance / Happer / Roy | `devdocs/MICHAELA_SYSTEM_MODEL.md` |
| LLM provider | **None in this repo** — PRD v1.2.6 dropped `api/llm.py` + the anthropic SDK. Skills are deterministic. Provider auth, model selection, and budget tracking live with Michaela's bench in `/root/michealaai`. | PRD v1.2.6 changelog |
| **Data layer** | **Supabase via `supabase-py` AsyncClient (PostgREST). No SQLAlchemy/asyncpg/Alembic.** | PRD v1.2.4, `devdocs/CURRENT_STATE.md` |
| **Schema mgmt** | **`supabase/migrations/*.sql` applied with `supabase db push`** | PRD v1.2.4 |
| **Auth** | Supabase JWT (`AuthenticatedUser`) for users, X-Internal-API-Key (`InternalActor`) for sub-agent writebacks | `api/auth.py` |
| Schema source | `/schemas/*.json` JSON Schema; Python codegen via `make schemas`; TS codegen not wired yet | `CONTRACTS.md §2` |
| Frontend hosting | Vercel for `/web` + `/landing`; VX1 hosts FastAPI + Redis + nginx; Supabase hosts DB/Auth/Storage | PRD §7.1, §7.6 |
| Fixture set | strong-pursue, maybe-needs-partner, reject, adversarial-image-pdf | PRD §5.4, `FIXTURES.md` |
| Eligibility rule | §11.1 — uncertainty = score 0 + critical blocker, never soft penalty. **Gabby owns the gate.** | PRD §11.1, `api/skills/score_fit/skill.py` |
| Cost ceiling | **N/A in this repo** — moved to Michaela (PRD v1.2.6) | PRD v1.2.6 changelog |
| Step/time budget | **N/A in this repo** — moved to Michaela (PRD v1.2.6) | PRD v1.2.6 changelog |
| **No Docker** | Local dev and VX1 prod both run Redis + FastAPI + nginx + Hermes as native services. Postgres/Auth/Storage live in Supabase. | 2026-05-09 |

---

## Decision log (append-only)

- **2026-05-09** — PRD v1.2.1 frozen; Vultr VX1 locked as deployment target.
- **2026-05-09** — Anthropic Claude chosen as LLM provider per PRD §17 Q1.
- **2026-05-09** — Adopted `hermes-agent` (Nous Research) as runtime/tool harness. Michaela remains the product workloop. OpenClaw narrowed to optional channel/tool substrate. PRD bumped to v1.2.2.
- **2026-05-09** — **No Docker, anywhere.** Both local dev and VX1 run Redis + FastAPI + nginx + Hermes as native services. Postgres/Auth/Storage live in Supabase.
- **2026-05-09** — **Adopted Supabase for Postgres + Storage** (PRD v1.2.3). Postgres off VX1 onto Supabase; raw + parsed solicitation files in the `govcapture-attachments` bucket. Redis stays native on VX1 for SSE.
- **2026-05-09** — **A4 + A5 landed.** `parse_pdf` (pypdf, no OCR per PRD §17 Q2) and `extract_requirements` (Anthropic structured outputs, page-bounds + evidence-binding validation per PRD §11).
- **2026-05-09** — **Phase 0 merged** (`dc9d1d8`). POST analysis writes, `/web` skeleton, fixture template — all live on `main`. Two-track dev1/dev2 layout retired; active work happens on `main` with per-feature branches.
- **2026-05-09** — **Michaela bench named.** The runtime bench is seven named agents: Michaela (CEO), Scot (discovery), Lenny (fit ranking), Gate (eligibility — §11.1 owner), Ledger (competitive intel), Happer (execution runner), Roy (packaging). Legacy 5-agent labels (Capture Lead / Compliance Officer / Risk Analyst / Proposal Strategist) are retired.
- **2026-05-09** — **PRD v1.2.4 — Postgres tooling rip-out.** SQLAlchemy / asyncpg / Alembic dropped. Data layer is `supabase-py` PostgREST. Schema lives in `supabase/migrations/*.sql` applied via `supabase db push`. Auth + ownership added: Supabase JWT for users, X-Internal-API-Key for sub-agent writebacks. New env vars: `INTERNAL_API_KEY`, `CORS_ALLOWED_ORIGINS`. Removed env: `DATABASE_URL`, `OPENAI_*`.
- **2026-05-09** — **PRD v1.2.5 — capability-pack boundary.** In-repo `api/agent/` orchestration was removed. `POST /agent-runs` now queues/persists a row; `/root/michealaai` owns Michaela's runtime and worker bench. This repo owns tools, data, API, landing, and `/web`.
- **2026-05-09** — **Sprint B — HTTP `/tools` parity.** Added internal `POST /tools/<name>` wrappers for the shipped GovCon skills so non-Hermes callers can invoke pack mechanics through FastAPI with `X-Internal-API-Key`.
- **2026-05-10** — **Launch-runway sprint complete.** Phases 1–5 landed in 12 commits: per-agent gck_ API keys + `/api/v1/tools/<name>` public mirror with rate limiting (3c9a7de, 1b239c6, a63bf30); `mcp-server-govcapture` MCP wrapper (966fa96); `query_usaspending` skill + `competitor_history` table for Ledger (b334c20, ec7eb5f, 3b19e39); `/agents` SEO landing + `robots.txt` + JSON-LD (e8e2500); `/web` SSE upgrade + same-origin proxy + loading skeletons + error boundaries (5628129, 94120fd); eval-harness scaffolding (b420fd5). Final state: 53 routes, 11 skills, 183 tests, ruff/mypy clean. Schema gap: migrations `20260510120000` (api_keys) and `20260510120100` (competitor_history) are committed but not yet `supabase db push`-ed; remote also carries two unvendored migrations (`20260510021500`, `20260510024000`) — see `devdocs/CURRENT_STATE.md` §10 schema-state table.
- **2026-05-10** — **Post-runway fix patch.** `query_usaspending` now sends the `award_type_codes` filter required by USASpending; the field is also exposed by the Hermes plugin and MCP server (5ff99cb, 310bb). `landing/next.config.mjs` adds `transpilePackages: ['lucide-react']` to work around the Next 15 ESM-resolution bug for that package (a03591f).
- **2026-05-10** — **Bench naming reconciled with Michaela's runtime.** Worker labels in this repo's docs renamed: Gate → Gabby (eligibility), Ledger → Lance (competitive intel). The other four workers (Scot, Lenny, Happer, Roy) and Michaela the orchestrator unchanged. Old names retained in PRD/historical changelog entries only. See PRD v1.2.6 changelog and `docs/superpowers/plans/2026-05-10-everything-to-v1.0.0.md` Phase 2.1.
- **2026-05-10** — **Weekly opportunity email approved (PRD v1.2.6).** Standalone outbound channel: one curated federal opportunity per week to opted-in waitlist signups via Resend. Pick path is **pure-LLM auto-selection** with deterministic safety filters (no narrow set-asides, deadline ≥ 14 days, no clearance/CUI keywords, US POP). PRD §6 wording corrected — "Real email sending" now reads "Real proposal submission via email" so weekly emails are unambiguously in scope. New §5.14, new §17 Q10. Reuses `INTERNAL_API_KEY` for cron auth; reuses the existing `waitlist_signups` table (extended with email-preference columns); two new tables `weekly_opportunity_picks` and `weekly_opportunity_email_log`. Two systemd timers on VX1 (Sun 22:00 UTC pick, Mon 14:00 UTC send). Dry-run by default; production-mode validator refuses to start when `EMAIL_DRY_RUN=false` AND legal footer is empty. Build brief: `tasks/dev1-backend/tasks/A14.md`. First test send confirmed via Resend sandbox (`onboarding@resend.dev` → Resend account-owner inbox); Resend message ID `4b04efba-0022-45e4-a885-fcc42f45d694`. **Implementation is spec'd, not yet built.**
