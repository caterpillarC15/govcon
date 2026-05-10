import Link from 'next/link'
import { ArrowRight, Building2, Compass, KeyRound, Sparkles } from 'lucide-react'
import { requireUser } from '@/lib/supabase/auth'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import { PageHeader } from '@/components/PageHeader'
import { ButtonLink } from '@/components/Button'
import { ErrorBanner } from '@/components/Field'
import type { CompanyProfile } from '@/lib/types'

export const dynamic = 'force-dynamic'

export default async function AppHome() {
  const { user, token } = await requireUser()

  let profiles: CompanyProfile[] = []
  let loadError: string | null = null
  try {
    profiles = await api.listCompanyProfiles(token)
  } catch (err) {
    loadError =
      err instanceof ApiError ? err.message : 'Could not load profiles.'
  }

  const hasProfile = profiles.length > 0
  const firstName = user.email?.split('@')[0] ?? 'there'

  if (!hasProfile && !loadError) {
    return <Onboarding firstName={firstName} />
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Bid desk"
        title={`Welcome back, ${firstName}`}
        subtitle="Pick a profile and start a new run, or jump back into a recent one."
        actions={
          <ButtonLink href="/app/goal" variant="primary">
            <Sparkles size={15} aria-hidden /> Start a run
          </ButtonLink>
        }
      />

      {loadError ? <ErrorBanner message={loadError} /> : null}

      <Card>
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-[var(--color-ink-muted)]">
              Your profiles
            </p>
            <h2 className="mt-1 text-[18px] font-semibold text-[var(--color-ink)]">
              {profiles.length} on file
            </h2>
          </div>
          <Link
            href="/app/profile"
            className="text-[13px] font-medium text-[var(--color-accent)] underline-offset-4 hover:underline"
          >
            Manage
          </Link>
        </div>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2">
          {profiles.map((profile) => (
            <li key={profile.id}>
              <Link
                href={`/app/profile/${profile.id}`}
                className="glass-subtle block rounded-2xl p-4 transition hover:-translate-y-[1px] hover:shadow-[0_14px_36px_-22px_rgba(15,23,42,0.32)]"
              >
                <p className="text-[13.5px] font-semibold text-[var(--color-ink)]">
                  {profile.name}
                </p>
                <p className="mt-1 text-[11.5px] text-[var(--color-ink-muted)]">
                  {profile.naics_codes.join(', ') || 'No NAICS'} ·{' '}
                  {profile.small_business_status
                    ? 'Small business'
                    : 'Not registered SB'}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}

function Onboarding({ firstName }: { firstName: string }) {
  return (
    <div className="space-y-6">
      <header>
        <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-[var(--color-ink-muted)]">
          Welcome to SamRail
        </p>
        <h1 className="mt-2 text-[34px] font-semibold leading-[1.05] tracking-[-0.01em] text-[var(--color-ink)]">
          Hi {firstName} — let&apos;s set up your bid desk.
        </h1>
        <p className="mt-3 max-w-xl text-[15px] leading-[1.55] text-[var(--color-ink-muted)]">
          Three quick steps before your first run. Each takes a minute.
        </p>
      </header>

      <ol className="grid gap-4 sm:grid-cols-3">
        <Step
          n={1}
          icon={<Building2 size={18} aria-hidden />}
          title="Add a company profile"
          body="Capabilities, NAICS, certifications, clearance. Used by Gate (eligibility) and Lenny (fit ranking)."
          cta={
            <ButtonLink href="/app/profile/new" variant="primary" size="md">
              Create profile
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/15">
                <ArrowRight size={12} strokeWidth={2.25} aria-hidden />
              </span>
            </ButtonLink>
          }
          active
        />
        <Step
          n={2}
          icon={<Compass size={18} aria-hidden />}
          title="Queue your first run"
          body="Describe what you want. Michaela qualifies opportunities and drafts a bid plan."
          locked
        />
        <Step
          n={3}
          icon={<KeyRound size={18} aria-hidden />}
          title="Mint an agent key (optional)"
          body="Per-agent gck_… keys for the public tool API. Skip if you only use the web app."
          locked
        />
      </ol>

      <Card>
        <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-[var(--color-ink-muted)]">
          What stays in your control
        </p>
        <ul className="mt-3 grid gap-2 sm:grid-cols-3">
          <Stay label="Bid/no-bid is yours" />
          <Stay label="Approval gate before any external artifact" />
          <Stay label="No CUI / classified data" />
        </ul>
      </Card>
    </div>
  )
}

function Step({
  n,
  icon,
  title,
  body,
  cta,
  active,
  locked,
}: {
  n: number
  icon: React.ReactNode
  title: string
  body: string
  cta?: React.ReactNode
  active?: boolean
  locked?: boolean
}) {
  return (
    <li
      className={
        active
          ? 'glass-strong rounded-[var(--radius-card)] p-5'
          : 'glass-subtle rounded-[var(--radius-card)] p-5 opacity-80'
      }
    >
      <div className="flex items-center gap-2">
        <span className="grid h-7 w-7 place-items-center rounded-full bg-[var(--color-ink)] text-[12px] font-semibold text-white">
          {n}
        </span>
        <span className="text-[var(--color-ink-muted)]">{icon}</span>
      </div>
      <h3 className="mt-3 text-[15px] font-semibold text-[var(--color-ink)]">
        {title}
      </h3>
      <p className="mt-1 text-[13px] leading-[1.5] text-[var(--color-ink-muted)]">
        {body}
      </p>
      <div className="mt-4">
        {cta ?? (
          <span className="inline-flex h-9 items-center rounded-full border border-[var(--color-canvas-border)] bg-white/60 px-3 text-[12px] font-medium text-[var(--color-ink-subtle)]">
            {locked ? 'Comes after step 1' : 'Up next'}
          </span>
        )}
      </div>
    </li>
  )
}

function Stay({ label }: { label: string }) {
  return (
    <li className="rounded-2xl border border-[var(--color-canvas-border)] bg-white/60 px-3 py-2 text-[13px] text-[var(--color-ink)]">
      {label}
    </li>
  )
}
