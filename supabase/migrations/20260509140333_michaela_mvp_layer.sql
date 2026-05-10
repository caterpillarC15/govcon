-- Michaela MVP layer
--
-- Adds the five tables needed for the Michaela UI / agent workflow that were
-- not part of the core govbase-style schema:
--
--   profiles           — one public row per auth.users entry (Supabase Auth)
--   opportunity_matches— customer-specific scoring per opportunity
--   documents          — metadata-only pointer to PDFs/files in R2 / Supabase Storage
--   document_chunks    — parsed page-level text for evidence search + citations
--   run_events         — append-only trace log tied to agent_runs
--
-- Conventions (same as core migration):
--   - All lowercase snake_case, plural table names.
--   - UUIDs default to extensions.gen_random_uuid().
--   - JSONB defaults to '[]'::jsonb / '{}'::jsonb.
--   - RLS enabled on every table; no policies yet (service_role bypasses RLS).
--   - updated_at maintained by the set_updated_at() trigger already defined.

set search_path = public, extensions;

-- ─────────────────────────────────────────────────────────────────
-- profiles
-- One row per Supabase Auth user.  id is a FK into auth.users so
-- deleting a user cascades cleanly.
-- ─────────────────────────────────────────────────────────────────
create table public.profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  email        text,
  full_name    text,
  company_name text,
  role         text not null default 'owner'
               check (role in ('owner','consultant','admin')),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create trigger trg_profiles_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;

-- ─────────────────────────────────────────────────────────────────
-- opportunity_matches
-- Customer-specific scoring result for one opportunity.
-- The same opportunity can score differently for different profiles.
-- ─────────────────────────────────────────────────────────────────
create table public.opportunity_matches (
  id                  uuid primary key default extensions.gen_random_uuid(),
  company_profile_id  uuid not null references public.company_profiles(id) on delete cascade,
  opportunity_id      uuid not null references public.opportunities(id)    on delete cascade,
  agent_run_id        uuid references public.agent_runs(id) on delete set null,
  agent_name          text,
  score               numeric(5,2),
  verdict             text not null default 'watch'
                      check (verdict in ('pursue','maybe','watch','skip')),
  days_left           integer,
  matched_keywords    jsonb not null default '[]'::jsonb,
  strengths           jsonb not null default '[]'::jsonb,
  gaps                jsonb not null default '[]'::jsonb,
  risk_flags          jsonb not null default '[]'::jsonb,
  known_gaps          jsonb not null default '[]'::jsonb,
  confidence          numeric(4,3),
  review_status       text not null default 'pending'
                      check (review_status in ('pending','reviewed','actioned')),
  created_at          timestamptz not null default now()
);
create index idx_opportunity_matches_company_profile_id on public.opportunity_matches(company_profile_id);
create index idx_opportunity_matches_opportunity_id     on public.opportunity_matches(opportunity_id);
create index idx_opportunity_matches_verdict            on public.opportunity_matches(verdict);
create index idx_opportunity_matches_score              on public.opportunity_matches(score desc nulls last);

alter table public.opportunity_matches enable row level security;

-- ─────────────────────────────────────────────────────────────────
-- documents
-- Metadata-only pointer to a file.  The binary lives in R2 /
-- Supabase Storage; storage_key is the canonical path.
-- ─────────────────────────────────────────────────────────────────
create table public.documents (
  id               uuid primary key default extensions.gen_random_uuid(),
  opportunity_id   uuid not null references public.opportunities(id) on delete cascade,
  source_url       text,
  file_name        text,
  file_type        text
                   check (file_type is null or file_type in ('pdf','docx','html','txt','csv','other')),
  storage_provider text not null default 'supabase',
  storage_bucket   text,
  storage_key      text not null,
  public_url       text,
  sha256           text,
  byte_size        bigint,
  page_count       integer,
  parse_status     text not null default 'pending'
                   check (parse_status in ('pending','parsed','failed','unparseable')),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);
create index idx_documents_opportunity_id on public.documents(opportunity_id);
create index idx_documents_parse_status   on public.documents(parse_status);
create trigger trg_documents_updated_at
before update on public.documents
for each row execute function public.set_updated_at();

alter table public.documents enable row level security;

-- ─────────────────────────────────────────────────────────────────
-- document_chunks
-- Parsed page-level text segments for evidence search and
-- page-number citations.  text stays in Postgres for MVP;
-- embedding column is nullable and reserved for later.
-- ─────────────────────────────────────────────────────────────────
create table public.document_chunks (
  id              uuid primary key default extensions.gen_random_uuid(),
  document_id     uuid not null references public.documents(id)     on delete cascade,
  opportunity_id  uuid not null references public.opportunities(id) on delete cascade,
  page_number     integer,
  chunk_index     integer not null,
  text            text not null,
  char_count      integer generated always as (length(text)) stored,
  created_at      timestamptz not null default now()
);
create index idx_document_chunks_document_id    on public.document_chunks(document_id);
create index idx_document_chunks_opportunity_id on public.document_chunks(opportunity_id);

alter table public.document_chunks enable row level security;

-- ─────────────────────────────────────────────────────────────────
-- run_events
-- Append-only trace log for an agent_run — one row per step/event.
-- event_type mirrors the SSE event names used by the FastAPI stream.
-- ─────────────────────────────────────────────────────────────────
create table public.run_events (
  id          uuid primary key default extensions.gen_random_uuid(),
  run_id      uuid not null references public.agent_runs(id) on delete cascade,
  event_type  text not null,
  agent_name  text,
  message     text,
  payload     jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index idx_run_events_run_id     on public.run_events(run_id);
create index idx_run_events_created_at on public.run_events(created_at);

alter table public.run_events enable row level security;

comment on table public.profiles          is 'One row per Supabase Auth user; id is a FK into auth.users.';
comment on table public.opportunity_matches is 'Customer-specific scoring result per opportunity. Same opp can score differently for different profiles.';
comment on table public.documents         is 'Metadata pointer to a solicitation attachment. Binary lives in R2/Supabase Storage; storage_key is canonical.';
comment on table public.document_chunks   is 'Parsed page-level text for evidence search and citation. text stays in Postgres for MVP; embedding is reserved.';
comment on table public.run_events        is 'Append-only trace log for an agent_run. Mirrors SSE event stream.';
