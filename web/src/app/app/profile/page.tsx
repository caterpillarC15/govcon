import Link from 'next/link'
import { Plus } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import type { CompanyProfile } from '@/lib/types'

export const dynamic = 'force-dynamic'

async function getToken(): Promise<string | null> {
  const supabase = await createClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

export default async function ProfilesPage() {
  const token = await getToken()
  if (!token) return null

  let profiles: CompanyProfile[] = []
  let loadError: string | null = null
  try {
    profiles = await api.listCompanyProfiles(token)
  } catch (err) {
    loadError =
      err instanceof ApiError ? err.message : 'Could not load profiles.'
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Profiles"
        title="Company profiles"
        subtitle="Switch between company contexts. Each profile holds a capability + eligibility fingerprint."
        actions={
          <Link
            href="/app/profile/new"
            className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            <Plus size={15} aria-hidden /> New profile
          </Link>
        }
      />

      {loadError ? (
        <Card className="border-red-200 bg-red-50/80 text-sm text-red-900">
          {loadError}
        </Card>
      ) : null}

      {profiles.length === 0 && !loadError ? (
        <EmptyState
          icon={<Plus size={28} />}
          title="No profiles yet"
          description="Add a profile to begin matching opportunities."
          action={
            <Link
              href="/app/profile/new"
              className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              Create profile
            </Link>
          }
        />
      ) : null}

      {profiles.length > 0 ? (
        <ul className="grid gap-3 sm:grid-cols-2">
          {profiles.map((profile) => (
            <li key={profile.id}>
              <Link
                href={`/app/profile/${profile.id}`}
                className="block rounded-2xl border border-slate-200 bg-white p-4 transition hover:border-slate-300 hover:bg-slate-50"
              >
                <p className="text-sm font-semibold text-slate-950">
                  {profile.name}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {profile.naics_codes.join(', ') || 'No NAICS'} ·{' '}
                  {profile.small_business_status
                    ? 'Small business'
                    : 'Not registered SB'}{' '}
                  · {profile.clearance_status ?? 'no clearance'}
                </p>
                {profile.capabilities.length > 0 ? (
                  <p className="mt-2 line-clamp-2 text-xs text-slate-600">
                    {profile.capabilities.join(', ')}
                  </p>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
