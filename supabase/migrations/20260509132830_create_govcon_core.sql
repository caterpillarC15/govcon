-- govcon core schema
--
-- Applies on top of the Supabase remote baseline (pulled via `supabase db pull`).
-- Mirrors PRD §8 + the govbase-style normalized SAM dimensions.
--
-- Conventions
-- - All identifiers lowercase snake_case, plural tables.
-- - PKs: UUIDs default to extensions.gen_random_uuid(); reference dimensions use IDENTITY.
-- - Hybrid: opportunities keep denormalized strings (agency, naics, psc_code, place_of_performance)
--   AND FKs into dimension tables. Server treats *_id as canonical; text columns are caches.
-- - JSONB defaults to '[]'::jsonb / '{}'::jsonb for stable inserts.
-- - updated_at is maintained by trigger (so SQL Editor + PostgREST writes refresh it too).
-- - RLS is enabled on every app table; no policies yet (server uses service_role and bypasses RLS).

set search_path = public, extensions;

-- ─────────────────────────────────────────────────────────────────
-- Helpers
-- ─────────────────────────────────────────────────────────────────
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ─────────────────────────────────────────────────────────────────
-- Reference dimensions (govbase pattern: lookup tables for joins/filters)
-- ─────────────────────────────────────────────────────────────────
create table public.psc_codes (
  id          bigint generated always as identity primary key,
  psc_code    text not null unique,
  name        text not null,
  description text,
  created_at  timestamptz not null default now()
);

create table public.naics_codes (
  id          bigint generated always as identity primary key,
  naics_code  text not null unique,
  title       text not null,
  description text,
  level       int,
  created_at  timestamptz not null default now()
);

create table public.agencies (
  id            uuid primary key default extensions.gen_random_uuid(),
  name          text not null,
  code          text unique,
  agency_slug   text,
  created_at    timestamptz not null default now()
);
create index idx_agencies_agency_slug on public.agencies(agency_slug);

create table public.agency_subsidiaries (
  id                uuid primary key default extensions.gen_random_uuid(),
  parent_agency_id  uuid not null references public.agencies(id) on delete cascade,
  name              text not null,
  code              text not null,
  created_at        timestamptz not null default now(),
  unique (parent_agency_id, code)
);
create index idx_agency_subsidiaries_parent on public.agency_subsidiaries(parent_agency_id);

create table public.locations (
  id            uuid primary key default extensions.gen_random_uuid(),
  city          text,
  state_code    text,
  country_code  text not null default 'US',
  display_name  text,
  created_at    timestamptz not null default now()
);
create index idx_locations_state_code on public.locations(state_code);

create table public.contacts (
  id          uuid primary key default extensions.gen_random_uuid(),
  full_name   text,
  email       text,
  phone       text,
  title       text,
  created_at  timestamptz not null default now()
);

-- ─────────────────────────────────────────────────────────────────
-- Domain tables (PRD §8)
-- ─────────────────────────────────────────────────────────────────
create table public.company_profiles (
  id                       uuid primary key default extensions.gen_random_uuid(),
  name                     text not null,
  website                  text,
  description              text,
  capabilities             jsonb not null default '[]'::jsonb,
  industry_keywords        jsonb not null default '[]'::jsonb,
  location                 text,
  service_area             jsonb not null default '[]'::jsonb,
  naics_codes              jsonb not null default '[]'::jsonb,
  certifications           jsonb not null default '[]'::jsonb,
  small_business_status    boolean not null default false,
  sam_status               text,
  clearance_status         text,
  past_performance         jsonb not null default '[]'::jsonb,
  insurance_bonding_status text,
  preferred_contract_size  text,
  preferred_role           text not null default 'either',
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);
create trigger trg_company_profiles_updated_at
before update on public.company_profiles
for each row execute function public.set_updated_at();

create table public.opportunities (
  id                    uuid primary key default extensions.gen_random_uuid(),
  source_notice_id      text unique,
  slug                  text not null unique
                         default replace(extensions.gen_random_uuid()::text, '-', ''),
  title                 text not null,
  agency                text not null,
  agency_id             uuid references public.agencies(id) on delete set null,
  agency_subsidiary_id  uuid references public.agency_subsidiaries(id) on delete set null,
  solicitation_number   text not null,
  notice_type           text,
  posted_date           date,
  due_date              date,
  office_name           text,
  psc_code              text,
  psc_code_id           bigint references public.psc_codes(id) on delete set null,
  naics                 text,
  naics_code_id         bigint references public.naics_codes(id) on delete set null,
  set_aside             text,
  place_of_performance  text,
  location_id           uuid references public.locations(id) on delete set null,
  description           text,
  attachments           jsonb not null default '[]'::jsonb,
  resource_links        jsonb not null default '[]'::jsonb,
  source_url            text,
  raw_payload           jsonb,
  opportunity_status    text not null default 'open'
                         check (opportunity_status in ('open','active','closed')),
  record_kind           text
                         check (record_kind is null or record_kind in ('rfp','contract')),
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);
create index idx_opportunities_due_date         on public.opportunities(due_date);
create index idx_opportunities_posted_date      on public.opportunities(posted_date);
create index idx_opportunities_agency_id        on public.opportunities(agency_id);
create index idx_opportunities_source_notice_id on public.opportunities(source_notice_id);
create trigger trg_opportunities_updated_at
before update on public.opportunities
for each row execute function public.set_updated_at();

create table public.opportunity_contacts (
  id              uuid primary key default extensions.gen_random_uuid(),
  opportunity_id  uuid not null references public.opportunities(id) on delete cascade,
  contact_id      uuid not null references public.contacts(id) on delete cascade,
  role            text,
  is_primary      boolean not null default false,
  started_at      timestamptz not null default now(),
  ended_at        timestamptz,
  created_at      timestamptz not null default now(),
  unique (opportunity_id, contact_id, started_at)
);
create index idx_opportunity_contacts_opportunity_id on public.opportunity_contacts(opportunity_id);
create index idx_opportunity_contacts_contact_id     on public.opportunity_contacts(contact_id);

create table public.extracted_requirements (
  id                uuid primary key default extensions.gen_random_uuid(),
  opportunity_id    uuid not null references public.opportunities(id) on delete cascade,
  type              text not null,
  title             text not null,
  value             text,
  description       text,
  confidence        text not null,
  evidence_snippet  text,
  source_document   text,
  page_number       int,
  is_blocker        boolean not null default false,
  created_at        timestamptz not null default now()
);
create index idx_extracted_requirements_opportunity_id on public.extracted_requirements(opportunity_id);

create table public.fit_scores (
  id                       uuid primary key default extensions.gen_random_uuid(),
  opportunity_id           uuid not null references public.opportunities(id) on delete cascade,
  company_profile_id       uuid not null references public.company_profiles(id) on delete cascade,
  total_score              int  not null,
  decision                 text not null,
  confidence               text not null,
  breakdown                jsonb not null default '{}'::jsonb,
  strengths                jsonb not null default '[]'::jsonb,
  weaknesses               jsonb not null default '[]'::jsonb,
  blockers                 jsonb not null default '[]'::jsonb,
  missing_info             jsonb not null default '[]'::jsonb,
  recommended_next_action  text,
  created_at               timestamptz not null default now()
);
create index idx_fit_scores_opportunity_id on public.fit_scores(opportunity_id);

create table public.risk_flags (
  id                       uuid primary key default extensions.gen_random_uuid(),
  opportunity_id           uuid not null references public.opportunities(id) on delete cascade,
  company_profile_id       uuid not null references public.company_profiles(id) on delete cascade,
  category                 text not null,
  severity                 text not null,
  title                    text not null,
  description              text not null,
  evidence                 text,
  mitigation               text,
  requires_human_review    boolean not null default false,
  created_at               timestamptz not null default now()
);
create index idx_risk_flags_opportunity_id on public.risk_flags(opportunity_id);
create index idx_risk_flags_severity       on public.risk_flags(severity);

create table public.action_packages (
  id                   uuid primary key default extensions.gen_random_uuid(),
  opportunity_id       uuid not null references public.opportunities(id) on delete cascade,
  company_profile_id   uuid not null references public.company_profiles(id) on delete cascade,
  executive_summary    text not null,
  decision             text not null,
  fit_score            int  not null,
  fit_rationale        text not null,
  compliance_matrix    jsonb not null default '[]'::jsonb,
  risk_register        jsonb not null default '[]'::jsonb,
  proposal_checklist   jsonb not null default '[]'::jsonb,
  timeline             jsonb not null default '[]'::jsonb,
  partner_suggestions  jsonb not null default '[]'::jsonb,
  outreach_draft       jsonb,
  approval_required    jsonb not null default '[]'::jsonb,
  created_at           timestamptz not null default now()
);

create table public.agent_runs (
  id                       uuid primary key default extensions.gen_random_uuid(),
  goal                     text not null,
  company_profile_id       uuid references public.company_profiles(id) on delete set null,
  status                   text not null default 'pending',
  steps                    jsonb not null default '[]'::jsonb,
  opportunities            jsonb not null default '[]'::jsonb,
  selected_opportunity_id  uuid references public.opportunities(id) on delete set null,
  action_package_id        uuid references public.action_packages(id) on delete set null,
  completed_at             timestamptz,
  created_at               timestamptz not null default now()
);
create index idx_agent_runs_status     on public.agent_runs(status);
create index idx_agent_runs_created_at on public.agent_runs(created_at);

-- ─────────────────────────────────────────────────────────────────
-- RLS — enable on every app table; no policies yet.
-- service_role (server) bypasses RLS; anon/authenticated have no
-- policies = no access. Auth wiring is deferred (PRD §17 Q5).
-- ─────────────────────────────────────────────────────────────────
alter table public.company_profiles       enable row level security;
alter table public.opportunities          enable row level security;
alter table public.opportunity_contacts   enable row level security;
alter table public.extracted_requirements enable row level security;
alter table public.fit_scores             enable row level security;
alter table public.risk_flags             enable row level security;
alter table public.action_packages        enable row level security;
alter table public.agent_runs             enable row level security;
alter table public.agencies               enable row level security;
alter table public.agency_subsidiaries    enable row level security;
alter table public.locations              enable row level security;
alter table public.contacts               enable row level security;
alter table public.psc_codes              enable row level security;
alter table public.naics_codes            enable row level security;

-- ─────────────────────────────────────────────────────────────────
-- Comments (handy in Supabase Studio / SQL Editor)
-- ─────────────────────────────────────────────────────────────────
comment on table public.opportunities is
  'Federal opportunity record (live SAM.gov / cached / seeded). source_notice_id is canonical external key; raw_payload is audit truth.';
comment on column public.opportunities.slug is
  'Stable URL segment; defaulted to gen_random_uuid hex if ingest does not supply one.';
comment on column public.opportunities.opportunity_status is
  'Lifecycle for UI filtering: open | active | closed (govbase Open/Active/Closed lowercased).';
comment on column public.opportunities.record_kind is
  'rfp | contract — distinguishes solicitation rows from already-awarded entries.';
comment on table public.opportunity_contacts is
  'Junction: opportunity ↔ contact, temporal (started_at/ended_at). Govbase solicitation_contacts pattern.';
comment on table public.psc_codes  is 'PSC reference (Product Service Code).';
comment on table public.naics_codes is 'NAICS reference (industry classification).';
