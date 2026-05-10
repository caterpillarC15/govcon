import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import { EmptyState } from '@/components/EmptyState'
import { PageHeader } from '@/components/PageHeader'
import type { CompanyProfile } from '@/lib/types'
import { GoalForm } from './GoalForm'

export const dynamic = 'force-dynamic'

async function getToken(): Promise<string | null> {
  const supabase = await createClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

export default async function GoalPage() {
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
      <Link
        href="/app"
        className="inline-flex items-center gap-1 text-sm font-medium text-blue-900 underline-offset-4 hover:underline"
      >
        <ChevronLeft size={14} aria-hidden /> Dashboard
      </Link>
      <PageHeader
        eyebrow="New run"
        title="What are you going after?"
        subtitle="Describe what you want, pick the company profile, and Michaela queues a run. Trace events stream into the run page."
      />

      {loadError ? (
        <Card className="border-red-200 bg-red-50/80 text-sm text-red-900">
          {loadError}
        </Card>
      ) : null}

      {profiles.length === 0 && !loadError ? (
        <EmptyState
          title="Create a profile first"
          description="A run needs a company profile so Gate (eligibility) and Lenny (fit) have context."
          action={
            <Link
              href="/app/profile/new"
              className="inline-flex h-10 items-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              Create profile
            </Link>
          }
        />
      ) : (
        <Card>
          <GoalForm profiles={profiles} />
        </Card>
      )}
    </div>
  )
}
