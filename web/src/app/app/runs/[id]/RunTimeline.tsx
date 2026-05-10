'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, Clock, Loader2, XCircle } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import { EmptyState } from '@/components/EmptyState'
import type { AgentRun, Opportunity, RunStatus, TraceEvent } from '@/lib/types'

const POLL_INTERVAL_MS = 2000
const TERMINAL_STATUSES: RunStatus[] = ['complete', 'partial', 'failed']

export function RunTimeline({
  initial,
  initialOpportunities,
}: {
  initial: AgentRun
  initialOpportunities: Opportunity[]
}) {
  const [run, setRun] = useState<AgentRun>(initial)
  const [opportunities, setOpportunities] =
    useState<Opportunity[]>(initialOpportunities)
  const [error, setError] = useState<string | null>(null)
  const cancelledRef = useRef(false)
  const supabase = createClient()

  useEffect(() => {
    cancelledRef.current = false

    async function poll() {
      if (cancelledRef.current) return
      try {
        const session = (await supabase.auth.getSession()).data.session
        if (!session) {
          setError('Session expired. Sign in again.')
          return
        }
        const next = await api.getAgentRun(session.access_token, run.id)
        if (cancelledRef.current) return
        setRun(next)
        if (next.opportunities.length !== opportunities.length) {
          const opps = await api.listAgentRunOpportunities(
            session.access_token,
            run.id,
          )
          if (!cancelledRef.current) setOpportunities(opps)
        }
        if (TERMINAL_STATUSES.includes(next.status)) return
      } catch (err) {
        if (cancelledRef.current) return
        setError(
          err instanceof ApiError ? err.message : 'Could not refresh run.',
        )
      }
      if (!cancelledRef.current) setTimeout(poll, POLL_INTERVAL_MS)
    }

    if (!TERMINAL_STATUSES.includes(run.status)) {
      const timeout = setTimeout(poll, POLL_INTERVAL_MS)
      return () => {
        cancelledRef.current = true
        clearTimeout(timeout)
      }
    }
    return () => {
      cancelledRef.current = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run.id])

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <StatusBadge status={run.status} />
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-slate-500">
                Status
              </p>
              <h2 className="text-lg font-semibold text-slate-950">
                {humanStatus(run.status)}
              </h2>
            </div>
          </div>
          {run.action_package_id ? (
            <Link
              href={`/app/action-packages/${run.action_package_id}`}
              className="inline-flex h-10 items-center gap-2 rounded-full bg-blue-900 px-4 text-sm font-medium text-white transition hover:bg-blue-800"
            >
              Open action package
            </Link>
          ) : null}
        </div>

        {error ? (
          <p
            className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-900"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <div className="mt-5">
          <p className="text-sm font-medium text-blue-900">Run timeline</p>
          <div className="mt-3 max-h-[360px] overflow-auto rounded-2xl border border-slate-200 bg-white">
            {run.steps.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">
                No trace events yet. Michaela has not written results for this run.
              </p>
            ) : (
              <ol className="divide-y divide-slate-100">
                {run.steps.map((event, index) => (
                  <li key={`${event.type}-${index}`} className="p-3">
                    <p className="text-sm font-medium text-slate-900">
                      {eventLabel(event)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {event.type}
                      {event.cost_usd != null
                        ? ` · $${event.cost_usd.toFixed(4)}`
                        : ''}
                      {event.latency_ms != null
                        ? ` · ${event.latency_ms}ms`
                        : ''}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </Card>

      {opportunities.length > 0 ? (
        <Card>
          <p className="text-sm font-medium text-blue-900">
            Ranked opportunities
          </p>
          <ul className="mt-3 grid gap-3">
            {opportunities.map((opportunity) => (
              <li key={opportunity.id}>
                <Link
                  href={`/app/opportunities/${opportunity.id}`}
                  className="block rounded-2xl border border-slate-200 bg-white p-4 transition hover:border-slate-300 hover:bg-slate-50"
                >
                  <p className="text-sm font-semibold text-slate-950">
                    {opportunity.title}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {opportunity.agency} ·{' '}
                    {opportunity.naics ?? 'NAICS unknown'} ·{' '}
                    {opportunity.due_date ?? 'No due date'}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      ) : run.status === 'pending' || run.status === 'running' ? (
        <EmptyState
          icon={<Loader2 size={28} className="animate-spin" />}
          title="Working…"
          description="Opportunities will appear here as Michaela ranks them."
        />
      ) : null}
    </div>
  )
}

function StatusBadge({ status }: { status: RunStatus }) {
  if (status === 'complete') {
    return <CheckCircle2 size={28} className="text-emerald-600" aria-hidden />
  }
  if (status === 'failed') {
    return <XCircle size={28} className="text-rose-600" aria-hidden />
  }
  if (status === 'running') {
    return (
      <Loader2 size={28} className="animate-spin text-blue-700" aria-hidden />
    )
  }
  return <Clock size={28} className="text-slate-500" aria-hidden />
}

function humanStatus(status: RunStatus) {
  switch (status) {
    case 'pending':
      return 'Queued for Michaela'
    case 'running':
      return 'Running'
    case 'complete':
      return 'Complete'
    case 'partial':
      return 'Complete with degraded results'
    case 'failed':
      return 'Failed'
  }
}

function eventLabel(event: TraceEvent) {
  if (event.type === 'tool_called') return `Tool called: ${event.tool}`
  if (event.type === 'tool_returned') return `Tool returned: ${event.tool}`
  if (event.type === 'step_started')
    return String(event.label ?? 'Step started')
  if (event.type === 'step_completed') return 'Step completed'
  if (event.type === 'opportunity_ranked') {
    return `Ranked ${event.decision} (${event.score ?? 0})`
  }
  if (event.type === 'run_started') return 'Run started'
  if (event.type === 'run_completed')
    return String(event.summary ?? 'Run completed')
  if (event.type === 'needs_human') return 'Needs human review'
  return event.type.replaceAll('_', ' ')
}
