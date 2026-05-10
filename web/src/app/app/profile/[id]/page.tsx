import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ChevronLeft } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import { PageHeader } from '@/components/PageHeader'
import type { CompanyProfile } from '@/lib/types'

export const dynamic = 'force-dynamic'

async function getToken(): Promise<string | null> {
  const supabase = await createClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

type Params = { id: string }

export default async function ProfileDetailPage({
  params,
}: {
  params: Promise<Params>
}) {
  const { id } = await params
  const token = await getToken()
  if (!token) return null

  let profile: CompanyProfile | null = null
  let loadError: string | null = null
  try {
    profile = await api.getCompanyProfile(token, id)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound()
    }
    loadError =
      err instanceof ApiError ? err.message : 'Could not load profile.'
  }

  if (!profile) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Profile" title="Profile not available" />
        {loadError ? (
          <Card className="border-red-200 bg-red-50/80 text-sm text-red-900">
            {loadError}
          </Card>
        ) : null}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Link
        href="/app/profile"
        className="inline-flex items-center gap-1 text-sm font-medium text-blue-900 underline-offset-4 hover:underline"
      >
        <ChevronLeft size={14} aria-hidden /> Back to profiles
      </Link>
      <PageHeader
        eyebrow="Profile"
        title={profile.name}
        subtitle={profile.description ?? undefined}
        actions={
          <button
            type="button"
            disabled
            title="Profile editing comes in a follow-up sprint."
            className="inline-flex h-10 items-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm font-medium text-slate-500 disabled:cursor-not-allowed"
          >
            Edit (coming soon)
          </button>
        }
      />

      <Card>
        <dl className="grid gap-4 sm:grid-cols-2">
          <Detail label="NAICS codes" value={profile.naics_codes.join(', ') || '—'} />
          <Detail
            label="Certifications"
            value={profile.certifications.join(', ') || '—'}
          />
          <Detail
            label="Capabilities"
            value={profile.capabilities.join(', ') || '—'}
          />
          <Detail label="Location" value={profile.location ?? '—'} />
          <Detail
            label="Clearance"
            value={profile.clearance_status ?? 'none'}
          />
          <Detail
            label="Small business"
            value={profile.small_business_status ? 'Yes' : 'No'}
          />
          <Detail label="Preferred role" value={profile.preferred_role} />
          <Detail
            label="Created"
            value={new Date(profile.created_at).toLocaleString()}
          />
        </dl>
      </Card>

      <div className="flex gap-3">
        <Link
          href={`/app/goal?profileId=${profile.id}`}
          className="inline-flex h-10 items-center gap-2 rounded-full bg-blue-900 px-4 text-sm font-medium text-white transition hover:bg-blue-800"
        >
          Start a run with this profile
        </Link>
      </div>
    </div>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-slate-900">{value}</dd>
    </div>
  )
}
