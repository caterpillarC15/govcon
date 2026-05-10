import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ChevronLeft } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import { PageHeader } from '@/components/PageHeader'
import type { ActionPackage } from '@/lib/types'
import { ApprovalGate } from './ApprovalGate'

export const dynamic = 'force-dynamic'

async function getToken(): Promise<string | null> {
  const supabase = await createClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

type Params = { id: string }

const DECISION_BAND_CLASS: Record<string, string> = {
  strong_pursue: 'bg-emerald-100 text-emerald-900 border-emerald-200',
  pursue: 'bg-sky-100 text-sky-900 border-sky-200',
  maybe: 'bg-amber-100 text-amber-900 border-amber-200',
  reject: 'bg-rose-100 text-rose-900 border-rose-200',
}

export default async function ActionPackagePage({
  params,
}: {
  params: Promise<Params>
}) {
  const { id } = await params
  const token = await getToken()
  if (!token) return null

  let pkg: ActionPackage | null = null
  let loadError: string | null = null

  try {
    pkg = await api.getActionPackage(token, id)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound()
    }
    loadError =
      err instanceof ApiError ? err.message : 'Could not load action package.'
  }

  if (!pkg) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Action package"
          title="Action package not available"
        />
        {loadError ? (
          <Card className="border-red-200 bg-red-50/80 text-sm text-red-900">
            {loadError}
          </Card>
        ) : null}
      </div>
    )
  }

  const bandClass = DECISION_BAND_CLASS[pkg.decision] ?? ''

  return (
    <div className="space-y-6">
      <Link
        href={`/app/opportunities/${pkg.opportunity_id}`}
        className="inline-flex items-center gap-1 text-sm font-medium text-blue-900 underline-offset-4 hover:underline"
      >
        <ChevronLeft size={14} aria-hidden /> Opportunity
      </Link>
      <PageHeader
        eyebrow="Action package"
        title={pkg.executive_summary.split('.')[0] || 'Bid memo'}
        subtitle={`Decision: ${pkg.decision.replaceAll('_', ' ')} · Fit ${pkg.fit_score}`}
        actions={
          <span
            className={`inline-flex h-10 items-center gap-2 rounded-full border px-4 text-sm font-medium ${bandClass}`}
          >
            {pkg.decision.replaceAll('_', ' ')}
          </span>
        }
      />

      <Card>
        <p className="text-sm font-medium text-blue-900">Executive summary</p>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {pkg.executive_summary}
        </p>
        <p className="mt-3 text-xs text-slate-500">
          <span className="font-medium">Rationale:</span> {pkg.fit_rationale}
        </p>
      </Card>

      {pkg.compliance_matrix.length > 0 ? (
        <Card>
          <p className="text-sm font-medium text-blue-900">Compliance matrix</p>
          <div className="mt-3 overflow-auto rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-[0.08em] text-slate-500">
                <tr>
                  <th className="p-3">Requirement</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Next action</th>
                  <th className="p-3">Owner</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pkg.compliance_matrix.map((row, i) => (
                  <tr key={`${row.requirement}-${i}`}>
                    <td className="p-3 font-medium text-slate-900">
                      {row.requirement}
                    </td>
                    <td className="p-3 text-slate-700">{row.status}</td>
                    <td className="p-3 text-slate-700">{row.next_action}</td>
                    <td className="p-3 text-slate-700">{row.owner}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}

      {pkg.proposal_checklist.length > 0 ? (
        <Card>
          <p className="text-sm font-medium text-blue-900">
            Proposal checklist
          </p>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {pkg.proposal_checklist.map((item, i) => (
              <li
                key={`${item}-${i}`}
                className="rounded-xl border border-slate-200 bg-white p-3"
              >
                {item}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {pkg.risk_register.length > 0 ? (
        <Card>
          <p className="text-sm font-medium text-blue-900">Risk register</p>
          <ul className="mt-3 space-y-2">
            {pkg.risk_register.map((r, i) => (
              <li
                key={`${r.risk}-${i}`}
                className="rounded-2xl border border-slate-200 bg-white p-3"
              >
                <p className="text-sm font-semibold text-slate-950">
                  {r.risk}
                </p>
                <p className="mt-1 text-xs text-slate-500">{r.severity}</p>
                {r.explanation ? (
                  <p className="mt-2 text-sm text-slate-700">{r.explanation}</p>
                ) : null}
                {r.mitigation ? (
                  <p className="mt-2 text-xs text-slate-700">
                    <span className="font-medium">Mitigation:</span>{' '}
                    {r.mitigation}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {pkg.outreach_draft ? (
        <Card>
          <p className="text-sm font-medium text-blue-900">Outreach draft</p>
          <p className="mt-2 text-sm font-semibold text-slate-950">
            {pkg.outreach_draft.subject}
          </p>
          <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">
            {pkg.outreach_draft.body}
          </p>
        </Card>
      ) : null}

      <Card>
        <p className="text-sm font-medium text-blue-900">Approval gate</p>
        <p className="mt-1 text-xs text-slate-500">
          All gates must be acknowledged before any external action. The pack
          does not enforce server-side; this UI is the gate.
        </p>
        <div className="mt-4">
          <ApprovalGate items={pkg.approval_required} />
        </div>
      </Card>
    </div>
  )
}
