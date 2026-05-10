'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useState } from 'react'
import { Loader2, Sparkles } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { api, ApiError } from '@/lib/api'
import type { CompanyProfile } from '@/lib/types'

const DEFAULT_GOAL =
  'Find cybersecurity and cloud migration opportunities in the next 90 days.'

function pickInitialProfile(
  profiles: CompanyProfile[],
  requested: string | null,
): string {
  // Honor ?profileId=… when it points at one of the user's owned profiles.
  // Otherwise fall back to the first profile (preserves prior behavior).
  if (requested && profiles.some((p) => p.id === requested)) {
    return requested
  }
  return profiles[0]?.id ?? ''
}

export function GoalForm({ profiles }: { profiles: CompanyProfile[] }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const supabase = createClient()
  const [profileId, setProfileId] = useState(() =>
    pickInitialProfile(profiles, searchParams.get('profileId')),
  )
  const [goal, setGoal] = useState(DEFAULT_GOAL)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!profileId) {
      setError('Pick a profile.')
      return
    }
    if (!goal.trim()) {
      setError('Enter a goal.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const session = (await supabase.auth.getSession()).data.session
      if (!session) {
        setError('Session expired. Sign in again.')
        return
      }
      const created = await api.createAgentRun(session.access_token, {
        goal: goal.trim(),
        profile_id: profileId,
      })
      router.push(`/app/runs/${created.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not queue run.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <label className="block">
        <span className="text-xs font-medium text-slate-600">Profile</span>
        <select
          value={profileId}
          onChange={(e) => setProfileId(e.target.value)}
          className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
        >
          {profiles.map((profile) => (
            <option key={profile.id} value={profile.id}>
              {profile.name}
            </option>
          ))}
        </select>
      </label>
      <label className="block">
        <span className="text-xs font-medium text-slate-600">Goal</span>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          rows={4}
          className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
        />
      </label>
      {error ? (
        <p
          className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-900"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={busy}
        className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-full bg-blue-900 px-4 text-sm font-medium text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {busy ? (
          <Loader2 size={15} className="animate-spin" aria-hidden />
        ) : (
          <Sparkles size={15} aria-hidden />
        )}
        {busy ? 'Queuing run…' : 'Queue run'}
      </button>
      <p className="text-xs text-slate-500">
        The run row is queued for Michaela. The orchestrator picks it up,
        drives the work, and writes results back. The run page polls for
        updates.
      </p>
    </form>
  )
}
