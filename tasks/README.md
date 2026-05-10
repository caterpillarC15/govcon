# Build Plan — joint reference docs

Active development happens on `main` directly with per-feature branches. The
canonical state-of-the-repo lives at `devdocs/CURRENT_STATE.md`. This
directory is the joint reference set: contracts, agent design, fixtures,
demo script, file ownership.

---

## Layout

```
tasks/
├── README.md                  ← you are here
├── CONTRACTS.md               ← schemas, SSE shapes, env, skill registry
├── AGENT_ARCHITECTURE.md      ← Michaela bench design (7 named agents)
├── INTERFERENCE_MAP.md        ← file ownership, shared-file protocols
├── FIXTURES.md                ← fixture content spec
└── DEMO.md                    ← §13.1 stage script + backup paths
```

Hermes runtime context: `HERMES.md` (repo root) and `.hermes/SOUL.md` —
both auto-loaded by the runtime.

---

## Working surface

- FastAPI proxy + 7-agent Michaela bench on Hermes runtime (Michaela +
  Scot/Lenny/Gabby/Lance/Happer/Roy)
- `supabase/migrations/*.sql` for schema (no Alembic)
- Next.js `/web` (product) + `/landing` (marketing) on Vercel
- Vultr VX1 hosts FastAPI + Hermes + Redis + nginx natively (no Docker)

---

## Frozen decisions

These are settled. Do not relitigate without a logged decision below.

| Area | Decision | Source |
|------|----------|--------|
| Hackathon track | Agents Track primary; optional Texas Open Data layer | PRD §17 Q9 |
| Deployment target | Vultr VX1 (16 vCPU / 64 GB / 960 GB / Ubuntu 24.04) | PRD §7.6 |
| Agent runtime | **hermes-agent** (Nous Research) — `.hermes/` configured with Michaela + 6 sub-agents; FastAPI seeded runner/bridge implemented; live Hermes CLI mode pending | `HERMES.md`, `tasks/AGENT_ARCHITECTURE.md` |
| Agent identities | Michaela / Scot / Lenny / Gabby / Lance / Happer / Roy | `tasks/AGENT_ARCHITECTURE.md` |
| LLM provider | Direct Anthropic Claude (Sonnet 4.6 + Haiku 4.5) via project env `ANTHROPIC_API_KEY`; OpenRouter is only a future routing option | `CONTRACTS.md §4`, `devdocs/MICHAELA_SYSTEM_MODEL.md` |
| **Data layer** | **Supabase via `supabase-py` AsyncClient (PostgREST). No SQLAlchemy/asyncpg/Alembic.** | PRD v1.2.4, `devdocs/CURRENT_STATE.md` |
| **Schema mgmt** | **`supabase/migrations/*.sql` applied with `supabase db push`** | PRD v1.2.4 |
| **Auth** | Supabase JWT (`AuthenticatedUser`) for users, X-Internal-API-Key (`InternalActor`) for sub-agent writebacks | `api/auth.py` |
| Schema source | `/schemas/*.json` JSON Schema; Python codegen via `make schemas`; TS codegen not wired yet | `CONTRACTS.md §2` |
| Frontend hosting | Vercel for `/web` + `/landing`; VX1 hosts FastAPI + Hermes + Redis + nginx; Supabase hosts DB/Auth/Storage | PRD §7.1, §7.6 |
| Fixture set | strong-pursue, maybe-needs-partner, reject, adversarial-image-pdf | PRD §5.4, `FIXTURES.md` |
| Eligibility rule | §11.1 — uncertainty = score 0 + critical blocker, never soft penalty. **Gabby is the gatekeeper.** | PRD §11.1, `tasks/AGENT_ARCHITECTURE.md` |
| Cost ceiling | $0.50 per agent run | PRD §17 Q1 |
| Step/time budget | 40 steps / 6 minutes per run | PRD §4.5 |
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
- **2026-05-09** — **Michaela bench named.** The runtime bench is seven named agents: Michaela (CEO), Scot (discovery), Lenny (fit ranking), Gabby (eligibility — §11.1 owner), Lance (competitive intel), Happer (execution runner), Roy (packaging). Legacy 5-agent labels (Capture Lead / Compliance Officer / Risk Analyst / Proposal Strategist) are retired.
- **2026-05-09** — **PRD v1.2.4 — Postgres tooling rip-out.** SQLAlchemy / asyncpg / Alembic dropped. Data layer is `supabase-py` PostgREST. Schema lives in `supabase/migrations/*.sql` applied via `supabase db push`. Auth + ownership added: Supabase JWT for users, X-Internal-API-Key for sub-agent writebacks. New env vars: `INTERNAL_API_KEY`, `CORS_ALLOWED_ORIGINS`, `DEMO_REPLAY_TRACE`. Removed env: `DATABASE_URL`, `OPENAI_*`.
