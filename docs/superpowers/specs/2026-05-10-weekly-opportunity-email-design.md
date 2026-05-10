# Weekly Opportunity Email — Design (PRD §5.14)

**Status:** approved by user 2026-05-10. Canonical spec is **PRD §5.14** plus the env contract in `tasks/CONTRACTS.md`. This file is a thin index and decomposition map; do not duplicate PRD prose here.

## Scope

One curated federal opportunity per week, delivered via Resend HTTP API to opted-in `waitlist_signups` rows. Idempotent per `(email, week_key)`. Dry-run by default. Refuses to send in production unless `EMAIL_LEGAL_FOOTER_ADDRESS` is set.

## Decomposition

| Phase | Surface | Files |
|-------|---------|-------|
| A | Data layer | `supabase/migrations/20260510130000_weekly_opportunity_email.sql`, `api/repositories/weekly_opportunity_pick.py`, `api/repositories/weekly_opportunity_email_log.py`, extension of `api/repositories/waitlist.py` |
| E | Config + production guard | `api/config.py` |
| D | Unsubscribe | `api/email/unsubscribe.py` (HMAC), `api/routes/email_subscriptions.py` |
| B | Auto-picker | `api/email/safety.py`, `api/jobs/auto_pick_weekly_opportunity.py`, `POST /internal/cron/auto-pick-weekly-opportunity` |
| C | Sender | `api/email/resend.py`, `api/email/render.py`, `api/jobs/send_weekly_opportunity.py`, `POST /internal/cron/weekly-opportunity-email` |
| F | Ops + tests | `infra/systemd/govcapture-cron-{auto-pick,weekly}.{service,timer}`, `api/tests/test_weekly_opportunity_email.py` |

## Trust boundaries

- Both cron routes gated by `InternalActor` (`X-Internal-API-Key`).
- Resend HTTP API called server-side only. `RESEND_API_KEY` never reaches the browser.
- Unsubscribe links carry only an HMAC token bound to `subscription_id + email`; raw IDs and emails never appear in URLs.
- All DB writes go through service-role Supabase client; RLS is enabled on the new tables with no public policies.

## Idempotency

- `weekly_opportunity_picks` PK on `week_key` — picker upsert is the de-dupe.
- `weekly_opportunity_email_log` unique on `(email, week_key)` — sender insert-then-send means re-runs short-circuit.
- `week_key` format: ISO week, `YYYY-WNN` (e.g., `2026-W19`), computed UTC.

## Production guard

`api/config.py` post-init check: when `EMAIL_DRY_RUN=false`, fail fast if any of `RESEND_API_KEY`, `EMAIL_UNSUBSCRIBE_SECRET`, `EMAIL_LEGAL_FOOTER_ADDRESS` is empty. Dev keeps `EMAIL_DRY_RUN=true` and the guard is a no-op.

## Out of scope (v1)

- Per-recipient profile-aware ranking (the picker uses one synthetic SMB profile for the whole list).
- Bounce/complaint webhook ingestion (the columns exist for a future Resend webhook handler).
- Double opt-in confirmation flow (column + flag exist, default `false`).
