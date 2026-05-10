import Link from 'next/link'
import { Plus, Sparkles } from 'lucide-react'
import { requireUser } from '@/lib/supabase/auth'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import type { CompanyProfile } from '@/lib/types'

export const dynamic = 'force-dynamic'

export default async function AppHome() {
  const { token } = await requireUser()

  let profiles: CompanyProfile[] = []
  let loadError: string | null = null
  try {
    profiles = await api.listCompanyProfiles(token)
  } catch (err) {
    loadError =
      err instanceof ApiError ? err.message : 'Could not load profiles.'
  }

  const hasProfile = profiles.length > 0

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Bid desk"
        title="Welcome back"
        subtitle={
          hasProfile
            ? 'Pick a profile and start a new run, or jump back into a recent one.'
            : 'Set up your company profile so Michaela can match opportunities.'
        }
        actions={
          hasProfile ? (
            <Link
              href="/app/goal"
              className="inline-flex h-10 items-center gap-2 rounded-full bg-blue-900 px-4 text-sm font-medium text-white transition hover:bg-blue-800"
            >
              <Sparkles size={15} aria-hidden /> Start a run
            </Link>
          ) : null
        }
      />

      {loadError ? (
        <Card className="border-red-200 bg-red-50/80 text-sm text-red-900">
          {loadError}
        </Card>
      ) : null}

      {!hasProfile ? (
        <EmptyState
          icon={<Plus size={28} />}
          title="No company profile yet"
          description="GovCapture matches opportunities to your capabilities, NAICS codes, certifications, and clearance level. Add a profile to begin."
          action={
            <Link
              href="/app/profile/new"
              className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              Create company profile
            </Link>
          }
        />
      ) : (
        <Card>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-blue-900">Your profiles</p>
              <h2 className="mt-1 text-lg font-semibold text-slate-950">
                {profiles.length} on file
              </h2>
            </div>
            <Link
              href="/app/profile"
              className="text-sm font-medium text-blue-900 underline-offset-4 hover:underline"
            >
              Manage
            </Link>
          </div>
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {profiles.map((profile) => (
              <li
                key={profile.id}
                className="rounded-2xl border border-slate-200 bg-white p-4"
              >
                <p className="text-sm font-semibold text-slate-950">
                  {profile.name}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {profile.naics_codes.join(', ') || 'No NAICS'} ·{' '}
                  {profile.small_business_status
                    ? 'Small business'
                    : 'Not registered SB'}
                </p>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
