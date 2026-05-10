-- PRD v1.2.5+: real approval persistence for action packages.
-- The orchestrator can read approved_at to gate downstream actions
-- (e.g., emailing the contracting officer). The pack itself only
-- writes these fields; it does not enforce gates server-side.

ALTER TABLE public.action_packages
  ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS approved_by UUID NULL
    REFERENCES auth.users(id) ON DELETE SET NULL;

COMMENT ON COLUMN public.action_packages.approved_at IS
  'Timestamp when an authorized user approved the package. Null = unapproved.';
COMMENT ON COLUMN public.action_packages.approved_by IS
  'Supabase auth user who approved. Set together with approved_at.';

-- RLS already enforces owner_profile_id; no policy change needed.
