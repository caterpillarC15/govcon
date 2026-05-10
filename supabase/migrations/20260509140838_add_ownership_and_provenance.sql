-- Add ownership and provenance columns missing from initial migrations
--
-- Gaps identified vs. schema-notes.md design:
--
--  1. company_profiles.owner_profile_id  → tie a profile to a Supabase Auth user
--  2. opportunity_matches.profile_id     → user-scoped match rows; required for RLS
--  3. agent_runs.profile_id              → user-scoped runs; required for RLS
--  4. opportunities.source               → provenance (sam.gov | manual | seed)
--  5. opportunities.active               → direct mirror of SAM "Active" flag;
--                                          Scot's filter logic uses it explicitly
--
-- All columns are nullable so existing rows are unaffected.
-- Indexes added where query patterns demand it.

set search_path = public, extensions;

-- ── 1. company_profiles ───────────────────────────────────────────────────
alter table public.company_profiles
  add column if not exists owner_profile_id uuid
    references public.profiles(id) on delete set null;

create index if not exists idx_company_profiles_owner_profile_id
  on public.company_profiles(owner_profile_id);

comment on column public.company_profiles.owner_profile_id is
  'Supabase Auth user who owns this profile. NULL = system/seed row.';

-- ── 2. opportunity_matches ────────────────────────────────────────────────
alter table public.opportunity_matches
  add column if not exists profile_id uuid
    references public.profiles(id) on delete set null;

create index if not exists idx_opportunity_matches_profile_id
  on public.opportunity_matches(profile_id);

comment on column public.opportunity_matches.profile_id is
  'User who triggered / owns this match result. Drives RLS row filtering.';

-- ── 3. agent_runs ─────────────────────────────────────────────────────────
alter table public.agent_runs
  add column if not exists profile_id uuid
    references public.profiles(id) on delete set null;

create index if not exists idx_agent_runs_profile_id
  on public.agent_runs(profile_id);

comment on column public.agent_runs.profile_id is
  'User who initiated this run. Drives RLS row filtering.';

-- ── 4. opportunities.source ───────────────────────────────────────────────
alter table public.opportunities
  add column if not exists source text not null default 'sam.gov';

comment on column public.opportunities.source is
  'Origin of this record: sam.gov | manual | seed. Default sam.gov for ingest rows.';

-- ── 5. opportunities.active ───────────────────────────────────────────────
alter table public.opportunities
  add column if not exists active boolean not null default true;

create index if not exists idx_opportunities_active
  on public.opportunities(active);

comment on column public.opportunities.active is
  'Direct mirror of SAM Active flag. Scot filters Active = true before scoring.';
