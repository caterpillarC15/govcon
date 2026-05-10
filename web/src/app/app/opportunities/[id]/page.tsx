import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ChevronLeft, ExternalLink } from 'lucide-react'
import { requireUser } from '@/lib/supabase/auth'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import { PageHeader } from '@/components/PageHeader'
import type {
  ExtractedRequirement,
  FitScore,
  Opportunity,
  RiskFlag,
} from '@/lib/types'

export const dynamic = 'force-dynamic'

type Params = { id: string }

const DECISION_BAND_CLASS: Record<string, string> = {
  strong_pursue: 'bg-emerald-100 text-emerald-900 border-emerald-200',
  pursue: 'bg-sky-100 text-sky-900 border-sky-200',
  maybe: 'bg-amber-100 text-amber-900 border-amber-200',
  reject: 'bg-rose-100 text-rose-900 border-rose-200',
}

const SEVERITY_CLASS: Record<string, string> = {
  critical_blocker: 'bg-rose-50 text-rose-900 border-rose-200',
  major_risk: 'bg-amber-50 text-amber-900 border-amber-200',
  moderate_risk: 'bg-sky-50 text-sky-900 border-sky-200',
  minor_concern: 'bg-slate-50 text-[var(--color-ink)] border-[var(--color-canvas-border)]',
}

export default async function OpportunityPage({
  params,
}: {
  params: Promise<Params>
}) {
  const { id } = await params
  const { token } = await requireUser()

  let opportunity: Opportunity | null = null
  let requirements: ExtractedRequirement[] = []
  let fit: FitScore | null = null
  let risks: RiskFlag[] = []
  const errors: string[] = []

  try {
    opportunity = await api.getOpportunity(token, id)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound()
    }
    errors.push(
      err instanceof ApiError ? err.message : 'Could not load opportunity.',
    )
  }

  // Best-effort: each downstream call may legitimately 404 if no analysis yet.
  await Promise.all([
    api.getOpportunityRequirements(token, id).then(
      (r) => {
        requirements = r
      },
      (err: unknown) => {
        if (!(err instanceof ApiError && err.status === 404)) {
          errors.push(
            err instanceof ApiError
              ? err.message
              : 'Could not load requirements.',
          )
        }
      },
    ),
    api.getOpportunityFitScore(token, id).then(
      (r) => {
        fit = r
      },
      (err: unknown) => {
        if (!(err instanceof ApiError && err.status === 404)) {
          errors.push(
            err instanceof ApiError ? err.message : 'Could not load fit.',
          )
        }
      },
    ),
    api.getOpportunityRisks(token, id).then(
      (r) => {
        risks = r
      },
      (err: unknown) => {
        if (!(err instanceof ApiError && err.status === 404)) {
          errors.push(
            err instanceof ApiError ? err.message : 'Could not load risks.',
          )
        }
      },
    ),
  ])

  if (!opportunity) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Opportunity"
          title="Opportunity not available"
        />
        {errors.length > 0 ? (
          <Card className="border-red-200 bg-red-50/80 text-sm text-red-900">
            {errors.join(' · ')}
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
        eyebrow={opportunity.agency}
        title={opportunity.title}
        subtitle={[
          opportunity.naics ? `NAICS ${opportunity.naics}` : null,
          opportunity.set_aside ? `Set-aside: ${opportunity.set_aside}` : null,
          opportunity.due_date ? `Due ${opportunity.due_date}` : null,
        ]
          .filter(Boolean)
          .join(' · ')}
        actions={
          opportunity.source_url ? (
            <Link
              href={opportunity.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--color-canvas-border)] bg-white px-4 text-sm font-medium text-[var(--color-ink)] transition hover:border-[var(--color-canvas-border)] hover:bg-slate-50"
            >
              SAM listing <ExternalLink size={14} aria-hidden />
            </Link>
          ) : undefined
        }
      />

      {opportunity.description ? (
        <Card>
          <p className="text-sm font-medium text-[var(--color-accent)]">Description</p>
          <p className="mt-2 text-sm leading-6 text-[var(--color-ink)]">
            {opportunity.description}
          </p>
        </Card>
      ) : null}

      {fit ? <FitCard fit={fit} /> : null}

      {requirements.length > 0 ? (
        <Card>
          <p className="text-sm font-medium text-[var(--color-accent)]">
            Requirements ({requirements.length})
          </p>
          <ul className="mt-3 space-y-2">
            {requirements.map((req) => (
              <li
                key={req.id}
                className="rounded-2xl border border-[var(--color-canvas-border)] bg-white p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-[var(--color-ink)]">
                    {req.title}
                  </p>
                  <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-[var(--color-ink-muted)]">
                    {req.type}
                  </span>
                </div>
                {req.value ? (
                  <p className="mt-1 text-xs text-[var(--color-ink-muted)]">{req.value}</p>
                ) : null}
                <p className="mt-2 text-xs text-[var(--color-ink-muted)]">
                  Confidence: {req.confidence}
                  {req.is_blocker ? ' · Blocker' : ''}
                  {req.page_number ? ` · p.${req.page_number}` : ''}
                </p>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {risks.length > 0 ? (
        <Card>
          <p className="text-sm font-medium text-[var(--color-accent)]">
            Risks ({risks.length})
          </p>
          <ul className="mt-3 space-y-2">
            {risks.map((risk) => (
              <li
                key={risk.id}
                className={`rounded-2xl border p-3 ${SEVERITY_CLASS[risk.severity] ?? ''}`}
              >
                <p className="text-sm font-semibold">{risk.title}</p>
                <p className="mt-1 text-xs">
                  {risk.severity.replaceAll('_', ' ')} · {risk.category}
                </p>
                {risk.description ? (
                  <p className="mt-2 text-sm">{risk.description}</p>
                ) : null}
                {risk.mitigation ? (
                  <p className="mt-2 text-xs">
                    <span className="font-medium">Mitigation:</span>{' '}
                    {risk.mitigation}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {errors.length > 0 ? (
        <Card className="border-amber-200 bg-amber-50 text-sm text-amber-900">
          <p className="font-medium">Some sections did not load</p>
          <ul className="mt-2 space-y-1">
            {errors.map((e) => (
              <li key={e}>· {e}</li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  )
}

function FitCard({ fit }: { fit: FitScore }) {
  const band = fit.decision
  const bandClass = DECISION_BAND_CLASS[band] ?? ''
  return (
    <Card>
      <p className="text-sm font-medium text-[var(--color-accent)]">Fit score</p>
      <div className="mt-2 flex items-baseline gap-3">
        <span className="text-4xl font-semibold text-[var(--color-ink)]">
          {fit.total_score}
        </span>
        <span
          className={`rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-wide ${bandClass}`}
        >
          {band.replaceAll('_', ' ')}
        </span>
        <span className="text-xs text-[var(--color-ink-muted)]">
          confidence: {fit.confidence}
        </span>
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {fit.strengths.length > 0 ? (
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-[var(--color-ink-muted)]">
              Strengths
            </p>
            <ul className="mt-2 space-y-1 text-sm text-[var(--color-ink)]">
              {fit.strengths.map((s) => (
                <li key={s}>· {s}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {fit.weaknesses.length > 0 ? (
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-[var(--color-ink-muted)]">
              Weaknesses
            </p>
            <ul className="mt-2 space-y-1 text-sm text-[var(--color-ink)]">
              {fit.weaknesses.map((s) => (
                <li key={s}>· {s}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      {fit.blockers.length > 0 ? (
        <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-rose-900">
            Blockers
          </p>
          <ul className="mt-2 space-y-1 text-sm text-rose-900">
            {fit.blockers.map((b) => (
              <li key={b}>· {b}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </Card>
  )
}
