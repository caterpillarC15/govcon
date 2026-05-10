-- supabase/migrations/20260510120100_add_competitor_history.sql
--
-- Adds the competitor_history table for Ledger's competitive-intel
-- writebacks. Replaces today's risk_flags-with-category=competitor_history
-- workaround. Per the launch-runway plan, the legacy rows stay (additive
-- migration, no backfill, no delete) — both surfaces work during the
-- transition.
--
-- Rows are written by the orchestrator (Ledger) via /api/v1/tools/
-- query-usaspending or via the InternalActor writeback path.

create table public.competitor_history (
  id                    uuid primary key default extensions.gen_random_uuid(),
  opportunity_id        uuid not null references public.opportunities(id) on delete cascade,
  owner_profile_id      uuid not null references public.profiles(id) on delete cascade,
  incumbent_name        text,
  awards                jsonb not null default '[]'::jsonb,
  total_obligated_usd   numeric(14,2),
  win_difficulty        text,
  evidence_url          text,
  created_at            timestamptz not null default now()
);

create index idx_comphist_opp on public.competitor_history(opportunity_id);
create index idx_comphist_own on public.competitor_history(owner_profile_id);

alter table public.competitor_history enable row level security;

create policy "owner can read own competitor history"
  on public.competitor_history
  for select
  using (owner_profile_id = (select auth.uid())::uuid);

create policy "owner can insert own competitor history"
  on public.competitor_history
  for insert
  with check (owner_profile_id = (select auth.uid())::uuid);
