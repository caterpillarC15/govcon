-- Persist public beta waitlist signups.
--
-- The public landing page posts to FastAPI, and FastAPI writes with the
-- service-role key. Browser clients do not write directly to this table.

set search_path = public, extensions;

create table if not exists public.waitlist_signups (
  id         uuid primary key default extensions.gen_random_uuid(),
  email      text not null,
  company    text,
  role       text,
  source     text not null default 'landing',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists idx_waitlist_signups_email_lower
  on public.waitlist_signups (lower(email));

create trigger trg_waitlist_signups_updated_at
before update on public.waitlist_signups
for each row execute function public.set_updated_at();

alter table public.waitlist_signups enable row level security;

comment on table public.waitlist_signups is
  'Public beta access requests. Written by FastAPI only; no direct browser writes.';
