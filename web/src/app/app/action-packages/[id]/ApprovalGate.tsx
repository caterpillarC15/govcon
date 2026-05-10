'use client'

import { useState } from 'react'
import { CheckCircle2 } from 'lucide-react'

export function ApprovalGate({ items }: { items: string[] }) {
  const [checked, setChecked] = useState<Record<number, boolean>>({})
  const [approved, setApproved] = useState(false)

  const allChecked = items.length > 0 && items.every((_, i) => checked[i])

  if (approved) {
    return (
      <div className="flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
        <CheckCircle2 size={16} aria-hidden />
        Approval recorded. The orchestrator will see this state on its next
        poll.
      </div>
    )
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
      <button
        type="button"
        disabled={!allChecked}
        onClick={() => setApproved(true)}
        className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-blue-900 px-4 text-sm font-medium text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        Approve & continue
      </button>
    </div>
  )
}
