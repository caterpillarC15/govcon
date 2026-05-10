'use client'

import { useState, useTransition } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { api, ApiError } from '@/lib/api'

export function ApprovalGate({
  packageId,
  token,
  items,
  initialApprovedAt,
}: {
  packageId: string
  token: string
  items: string[]
  initialApprovedAt: string | null
}) {
  const [checked, setChecked] = useState<Record<number, boolean>>({})
  const [approvedAt, setApprovedAt] = useState<string | null>(initialApprovedAt)
  const [error, setError] = useState<string | null>(null)
  const [pending, startTransition] = useTransition()

  if (approvedAt) {
    return (
      <div className="flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
        <CheckCircle2 size={16} aria-hidden />
        Approved {new Date(approvedAt).toLocaleString()}.
      </div>
    )
  }

  const allChecked = items.length > 0 && items.every((_, i) => checked[i])

  const handleApprove = () => {
    setError(null)
    startTransition(async () => {
      try {
        const updated = await api.approveActionPackage(token, packageId)
        setApprovedAt(updated.approved_at ?? new Date().toISOString())
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : 'Could not record approval — please try again.',
        )
      }
    })
  }

  return (
    <div className="space-y-3">
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i}>
            <label className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3 text-sm">
              <input
                type="checkbox"
                checked={!!checked[i]}
                onChange={(e) =>
                  setChecked((c) => ({ ...c, [i]: e.target.checked }))
                }
                className="mt-1"
              />
              <span>{item}</span>
            </label>
          </li>
        ))}
      </ul>
      {error ? (
        <p
          className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-900"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      <button
        type="button"
        disabled={!allChecked || pending}
        onClick={handleApprove}
        className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-blue-900 px-4 text-sm font-medium text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? 'Recording…' : 'Approve & continue'}
      </button>
    </div>
  )
}
