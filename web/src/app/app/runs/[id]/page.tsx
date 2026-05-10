import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ChevronLeft } from 'lucide-react'
import { requireUser } from '@/lib/supabase/auth'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import { PageHeader } from '@/components/PageHeader'
import type { AgentRun, Opportunity } from '@/lib/types'
import { RunTimeline } from './RunTimeline'

export const dynamic = 'force-dynamic'


type Params = { id: string }

export default async function RunDetailPage({
  params,
}: {
  params: Promise<Params>
}) {
  const { id } = await params
  const { token } = await requireUser()

  let run: AgentRun | null = null
  let opportunities: Opportunity[] = []
  let loadError: string | null = null

  try {
    run = await api.getAgentRun(token, id)
    opportunities = await api.listAgentRunOpportunities(token, id)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound()
    }
    loadError = err instanceof ApiError ? err.message : 'Could not load run.'
  }

  if (!run) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Run" title="Run not available" />
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
        href="/app"
        className="inline-flex items-center gap-1 text-sm font-medium text-[var(--color-accent)] underline-offset-4 hover:underline"
      >
        <ChevronLeft size={14} aria-hidden /> Dashboard
      </Link>
      <PageHeader
        eyebrow="Run"
        title={truncateGoal(run.goal)}
        subtitle={`Queued ${new Date(run.created_at).toLocaleString()} · Run ID ${run.id.slice(0, 8)}`}
      />

      <RunTimeline initial={run} initialOpportunities={opportunities} />
    </div>
  )
}

function truncateGoal(goal: string) {
  if (goal.length <= 80) return goal
  return goal.slice(0, 77) + '…'
}
