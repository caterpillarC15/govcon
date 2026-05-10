'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  XCircle,
} from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { api } from '@/lib/api'
import { Card } from '@/components/Card'
import { EmptyState } from '@/components/EmptyState'
import type { AgentRun, Opportunity, RunStatus, TraceEvent } from '@/lib/types'

const TERMINAL_STATUSES: RunStatus[] = ['complete', 'partial', 'failed']

type StreamState = 'idle' | 'open' | 'reconnecting' | 'closed'

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
  const [streamState, setStreamState] = useState<StreamState>('idle')
  // Memoize so React Strict Mode's double-render doesn't open a second
  // EventSource (createClient() returned a new client object per render
  // before this).
  const supabase = useMemo(() => createClient(), [])

  useEffect(() => {
    if (TERMINAL_STATUSES.includes(initial.status)) return undefined

    let stillMounted = true
    const es = new EventSource(`/api/run-stream/${run.id}`)
    es.addEventListener('open', () => {
      if (stillMounted) setStreamState('open')
    })

    async function fetchAndSetTerminal() {
      try {
        const session = (await supabase.auth.getSession()).data.session
        if (!session) return
        const next = await api.getAgentRun(session.access_token, run.id)
        if (!stillMounted) return
        setRun(next)
        const opps = await api.listAgentRunOpportunities(
          session.access_token,
          run.id,
        )
        if (stillMounted) setOpportunities(opps)
      } catch {
        /* swallow; UI already shows last-known state */
      }
    }

    function handle(rawType: string) {
      return (ev: Event) => {
        if (!stillMounted) return
        const data = (ev as MessageEvent).data
        let parsed: TraceEvent
        try {
          parsed = JSON.parse(data) as TraceEvent
        } catch {
          return
        }
        setRun((prev) => {
          // Dedup by step_id when present so server-rendered
          // initial.steps + an upstream replay don't double-render
          // each step. Events without step_id (run_started,
          // opportunity_ranked, needs_human) bypass the dedup.
          if (parsed.step_id) {
            const seen = prev.steps.some(
              (s) => s.step_id === parsed.step_id && s.type === parsed.type,
            )
            if (seen) return prev
          }
          return { ...prev, steps: [...prev.steps, parsed] }
        })
        if (rawType === 'run_completed') {
          es.close()
          setStreamState('closed')
          void fetchAndSetTerminal()
        }
      }
    }

    ;[
      'run_started',
      'step_started',
      'step_completed',
      'tool_called',
      'tool_returned',
      'opportunity_ranked',
      'needs_human',
      'run_completed',
    ].forEach((t) => es.addEventListener(t, handle(t)))

    es.onerror = () => {
      if (!stillMounted) return
      // EventSource auto-retries on transient drops while readyState is
      // CONNECTING; it gives up on hard errors and transitions to
      // CLOSED. Distinguish the two so the UI doesn't claim "retrying"
      // when nothing is.
      setStreamState(
        es.readyState === EventSource.CLOSED ? 'closed' : 'reconnecting',
      )
    }

    return () => {
      stillMounted = false
      es.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run.id, initial.status])

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

        {streamState === 'reconnecting' ? (
          <p
            className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900"
            role="status"
          >
            Reconnecting to live stream…
          </p>
        ) : null}
        {streamState === 'closed' &&
        !TERMINAL_STATUSES.includes(run.status) ? (
          <p
            className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-900"
            role="alert"
          >
            Live stream disconnected.{' '}
            <button
              type="button"
              onClick={() => location.reload()}
              className="font-medium underline underline-offset-2"
            >
              Refresh
            </button>{' '}
            to reconnect.
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
  if (status === 'partial') {
    // Distinct icon — was falling through to grey Clock identical to
    // 'pending', which contradicted the "Complete with degraded
    // results" label.
    return <AlertTriangle size={28} className="text-amber-600" aria-hidden />
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
