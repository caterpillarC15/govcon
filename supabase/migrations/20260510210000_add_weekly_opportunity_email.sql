-- PRD §5.14 — Weekly Opportunity Email
--
-- Standalone outbound channel: one curated federal opportunity per week,
-- sent via Resend HTTP API to opted-in waitlist subscribers. Additive
-- only — extends waitlist_signups in place and adds two new tables for
-- per-week curation and per-recipient idempotency.

set search_path = public, extensions;

-- 1. Subscriber preferences on the existing waitlist row.
alter table public.waitlist_signups
  add column if not exists weekly_opportunity_enabled boolean not null default true,
  add column if not exists unsubscribed_at            timestamptz,
  add column if not exists unsubscribed_reason        text,
  add column if not exists bounced_at                 timestamptz,
  add column if not exists complained_at              timestamptz,
  add column if not exists confirmed_at               timestamptz,
  add column if not exists last_emailed_at            timestamptz;

comment on column public.waitlist_signups.weekly_opportunity_enabled is
  'PRD §5.14 — opt-in toggle. Default true; landing form copy says "we will send you one curated federal opportunity each week".';
comment on column public.waitlist_signups.unsubscribed_at is
  'Set by GET /email-subscriptions/unsubscribe?token=… when HMAC verifies. Eligibility check filters this NOT NULL.';
comment on column public.waitlist_signups.confirmed_at is
  'Only consulted if EMAIL_REQUIRE_DOUBLE_OPT_IN=true. Default behavior treats every signup as confirmed.';

-- Eligibility lookup index (partial — only live subscriptions).
create index if not exists idx_waitlist_signups_eligible
  on public.waitlist_signups (created_at)
  where weekly_opportunity_enabled = true
    and unsubscribed_at is null
    and bounced_at is null
    and complained_at is null;

-- 2. Per-week pick (one row per ISO week). Manual override wins via
-- INSERT ON CONFLICT (week_key) DO NOTHING — auto-picker silently skips
-- if a curator pinned ahead of the Sunday 22:00 UTC fire.
create table if not exists public.weekly_opportunity_picks (
  id              uuid primary key default extensions.gen_random_uuid(),
  week_key        text not null unique,
  opportunity_id  uuid not null references public.opportunities(id) on delete cascade,
  source          text not null check (source in ('manual', 'llm_auto')),
  picker_audit    jsonb not null default '{}'::jsonb,
  picked_at       timestamptz not null default now()
);

comment on table public.weekly_opportunity_picks is
  'PRD §5.14 — one curated opportunity per ISO week. week_key format YYYY-Www, UTC.';
comment on column public.weekly_opportunity_picks.picker_audit is
  'JSONB log of candidates considered + filter rejections; populated by auto-picker for forensics.';

-- 3. Per-recipient send log. UNIQUE (email, week_key, email_type) is the
-- two-phase claim slot the send job fights over before calling Resend.
create table if not exists public.weekly_opportunity_email_log (
  id                  uuid primary key default extensions.gen_random_uuid(),
  email               text not null,
  week_key            text not null,
  email_type          text not null default 'weekly_opportunity'
                       check (email_type in ('weekly_opportunity', 'unsubscribe_confirm')),
  status              text not null
                       check (status in ('dry_run', 'pending', 'sent', 'failed')),
  resend_message_id   text,
  sent_at             timestamptz,
  failure_reason      text,
  created_at          timestamptz not null default now(),
  unique (email, week_key, email_type)
);

create index if not exists idx_weekly_email_log_week
  on public.weekly_opportunity_email_log (week_key, status);

comment on table public.weekly_opportunity_email_log is
  'PRD §5.14 — idempotent per (email, week_key, email_type). Send job INSERTs first then UPDATEs; dry-run mode writes status=dry_run.';

-- 4. RLS — admin/audit tables; service-role-only (BYPASSRLS) writes.
alter table public.weekly_opportunity_picks enable row level security;
alter table public.weekly_opportunity_email_log enable row level security;

-- No grant policies — server-side jobs use the service role key which
-- bypasses RLS. Browser/JWT writes are intentionally blocked.
