# API env contract

Every variable FastAPI (`api/config.py`) reads. Lives in root `.env` (gitignored locally) or `/opt/govcapture/.env` on VX1.

## Keys

```
SAM_API_KEY=
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_ANON_KEY=
SUPABASE_STORAGE_BUCKET=govcapture-attachments
INTERNAL_API_KEY=
REDIS_URL=redis://localhost:6379/0
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173
RESEND_API_KEY=
RESEND_FROM_EMAIL=GovCapture <onboarding@resend.dev>
RESEND_REPLY_TO=
EMAIL_PUBLIC_BASE_URL=http://localhost:8000
EMAIL_UNSUBSCRIBE_SECRET=
EMAIL_LEGAL_FOOTER_ADDRESS=
EMAIL_DRY_RUN=true
EMAIL_REQUIRE_DOUBLE_OPT_IN=false
EMAIL_AUTO_PICK_ENABLED=true
EMAIL_AUTO_PICK_MIN_SCORE=60
EMAIL_AUTO_PICK_MAX_CANDIDATES=20
EMAIL_NAICS_ALLOWLIST=
EMAIL_USE_FIXTURES_FOR_AUTO_PICK=false
```

## Per-key

| Variable | Required | Purpose |
|---|---|---|
| `SAM_API_KEY` | optional | Live SAM.gov; empty falls back to seeded fixtures |
| `SUPABASE_URL` | yes | Project URL — `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | yes | Server-only; bypasses RLS |
| `SUPABASE_ANON_KEY` | yes | Used by `require_user` JWT verifier |
| `SUPABASE_STORAGE_BUCKET` | yes | Default `govcapture-attachments` (bucket must exist, private) |
| `INTERNAL_API_KEY` | yes | Header for sub-agent writebacks; Bearer for `/internal/cron/*` |
| `REDIS_URL` | yes | SSE pub/sub bridge |
| `CORS_ALLOWED_ORIGINS` | yes | Comma-separated list of browser origins. Must include landing + app hosts |
| `RESEND_API_KEY` | yes (prod) | Resend API key for §5.14 weekly email |
| `RESEND_FROM_EMAIL` | yes | `GovCapture <noreply@verified-domain>` (or `onboarding@resend.dev` sandbox) |
| `RESEND_REPLY_TO` | optional | Custom Reply-To address |
| `EMAIL_PUBLIC_BASE_URL` | yes | Public URL the unsubscribe link uses (must be HTTPS in prod) |
| `EMAIL_UNSUBSCRIBE_SECRET` | yes (prod) | HMAC secret. Generate: `openssl rand -hex 32` |
| `EMAIL_LEGAL_FOOTER_ADDRESS` | yes (prod) | CAN-SPAM physical mailing address |
| `EMAIL_DRY_RUN` | yes | `true` suppresses Resend calls. Default `true`. Production must explicitly flip to `false` |
| `EMAIL_REQUIRE_DOUBLE_OPT_IN` | optional | Default `false`. If `true`, requires `confirmed_at` row before send |
| `EMAIL_AUTO_PICK_ENABLED` | optional | Default `true` — Sun cron picks the week's opportunity |
| `EMAIL_AUTO_PICK_MIN_SCORE` | optional | Default `60`. Floor for auto-picker score |
| `EMAIL_AUTO_PICK_MAX_CANDIDATES` | optional | Default `20`. Max opportunities scored per cron run |
| `EMAIL_NAICS_ALLOWLIST` | optional | Comma-separated NAICS codes; empty = no filter |
| `EMAIL_USE_FIXTURES_FOR_AUTO_PICK` | optional | Default `false`. Dev-only escape hatch |

## Production guard

`api/config.py` refuses to start if `EMAIL_DRY_RUN=false` AND any of `RESEND_API_KEY` / `EMAIL_UNSUBSCRIBE_SECRET` / `EMAIL_LEGAL_FOOTER_ADDRESS` is empty.

## Dropped at PRD v1.2.6

`ANTHROPIC_API_KEY`, `LLM_DEV_MODEL`, `LLM_SYNTH_MODEL`, `RUN_BUDGET_USD/STEPS/SECONDS`, `HERMES_HOME`, `HERMES_MODEL`, `DEMO_USE_SEEDED_ONLY`, `DEMO_REPLAY_TRACE`. Skills are deterministic; LLM cost + budget tracking lives with Michaela in `/root/michealaai`.
