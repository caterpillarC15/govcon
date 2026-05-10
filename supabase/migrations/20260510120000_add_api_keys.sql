-- supabase/migrations/20260510120000_add_api_keys.sql
--
-- Adds the api_keys table for per-user agent keys (gck_…). Augments the
-- single shared INTERNAL_API_KEY: the new /api/v1/tools/<name> routes
-- accept either header. RLS scopes a user to their own keys.
--
-- Plaintext key format (assembled by api/repositories/api_key.py):
--     gck_<urlsafe-base64 of 32 random bytes>
-- Stored: sha256(plaintext) in key_hash; first 12 chars of plaintext in
-- prefix (gck_ + 8 random chars) for display.
--
-- Scopes default to {tools:*}. Per-tool scope refinement is post-v1.

create table public.api_keys (
  id                  uuid primary key default extensions.gen_random_uuid(),
  owner_profile_id    uuid not null references public.profiles(id) on delete cascade,
  name                text not null,
  key_hash            text not null unique,
  prefix              text not null,
  scopes              text[] not null default '{tools:*}',
  last_used_at        timestamptz,
  revoked_at          timestamptz,
  created_at          timestamptz not null default now()
);

create index idx_api_keys_owner   on public.api_keys(owner_profile_id);
create index idx_api_keys_active  on public.api_keys(owner_profile_id) where revoked_at is null;

alter table public.api_keys enable row level security;

create policy "owner can read own keys"
  on public.api_keys
  for select
  using (owner_profile_id = (select auth.uid())::uuid);

create policy "owner can insert own keys"
  on public.api_keys
  for insert
  with check (owner_profile_id = (select auth.uid())::uuid);

create policy "owner can revoke own keys"
  on public.api_keys
  for update
  using (owner_profile_id = (select auth.uid())::uuid)
  with check (owner_profile_id = (select auth.uid())::uuid);
