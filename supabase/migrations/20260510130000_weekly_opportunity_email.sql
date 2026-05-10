-- Weekly Opportunity Email (PRD §5.14, v1.2.6).
--
-- Extends waitlist_signups with opt-in / suppression columns and adds two
-- new tables that carry per-week curation and per-recipient idempotency.
-- Service role bypasses RLS for FastAPI; no public policies are created.

set search_path = public, extensions;

-- ── waitlist_signups extensions ─────────────────────────────────────
alter table public.waitlist_signups
  add column if not exists weekly_opportunity_enabled boolean not null default true,
  add column if not exists confirmed_at         timestamptz,
  add column if not exists unsubscribed_at      timestamptz,
  add column if not exists unsubscribed_reason  text,
  add column if not exists bounced_at           timestamptz,
  add column if not exists complained_at        timestamptz,
  add column if not exists last_emailed_at      timestamptz;

create index if not exists idx_waitlist_eligible_for_email
  on public.waitlist_signups (weekly_opportunity_enabled)
  where unsubscribed_at is null
    and bounced_at      is null
    and complained_at   is null;

comment on column public.waitlist_signups.weekly_opportunity_enabled is
  'PRD §5.14 opt-in flag. Default true on signup; flip false on unsubscribe.';
comment on column public.waitlist_signups.confirmed_at is
  'Double-opt-in timestamp. Only consulted when EMAIL_REQUIRE_DOUBLE_OPT_IN=true.';

-- ── weekly_opportunity_picks ────────────────────────────────────────
-- One row per ISO week. Re-running the picker upserts on week_key.
create table if not exists public.weekly_opportunity_picks (
  week_key        text primary key,
  opportunity_id  uuid references public.opportunities(id) on delete set null,
  source          text not null default 'llm_auto'
                    check (source in ('llm_auto','manual','none')),
  score           numeric,
  confidence      text check (confidence is null or confidence in ('low','medium','high')),
  rationale       text,
  picker_audit    jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create trigger trg_weekly_opportunity_picks_updated_at
before update on public.weekly_opportunity_picks
for each row execute function public.set_updated_at();
alter table public.weekly_opportunity_picks enable row level security;

comment on table public.weekly_opportunity_picks is
  'PRD §5.14 weekly curated pick. week_key format YYYY-WNN (UTC ISO week).';
comment on column public.weekly_opportunity_picks.picker_audit is
  'JSON record of every candidate considered and reason for rejection.';

-- ── weekly_opportunity_email_log ────────────────────────────────────
-- Per-recipient idempotency record. Insert-then-send means re-runs of the
-- send job short-circuit on the unique constraint.
create table if not exists public.weekly_opportunity_email_log (
  id                  uuid primary key default extensions.gen_random_uuid(),
  email               text not null,
  week_key            text not null references public.weekly_opportunity_picks(week_key) on delete cascade,
  email_type          text not null default 'weekly_opportunity'
                       check (email_type in ('weekly_opportunity','unsubscribe_confirm')),
  status              text not null default 'pending'
                       check (status in ('pending','sent','dry_run','failed','suppressed')),
  resend_message_id   text,
  failure_reason      text,
  sent_at             timestamptz,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create unique index if not exists idx_email_log_email_week_type
  on public.weekly_opportunity_email_log (lower(email), week_key, email_type);
create index if not exists idx_email_log_week
  on public.weekly_opportunity_email_log (week_key);
create trigger trg_weekly_opportunity_email_log_updated_at
before update on public.weekly_opportunity_email_log
for each row execute function public.set_updated_at();
alter table public.weekly_opportunity_email_log enable row level security;

comment on table public.weekly_opportunity_email_log is
  'PRD §5.14 per-recipient send log. Unique (lower(email), week_key) is the idempotency key.';
