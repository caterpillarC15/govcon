'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  Play,
  ShieldCheck,
} from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { getApiBase } from '@/lib/api'

type CompanyProfile = {
  id: string
  name: string
  capabilities: string[]
  naics_codes: string[]
  certifications: string[]
  clearance_status?: string | null
  small_business_status: boolean
}

type AgentRun = {
  id: string
  goal: string
  status: 'pending' | 'running' | 'complete' | 'partial' | 'failed'
  opportunities: string[]
  selected_opportunity_id?: string | null
  action_package_id?: string | null
}

type TraceEvent = {
  type: string
  ts?: string
  label?: string
  tool?: string
  decision?: string
  score?: number
  summary?: string
  [key: string]: unknown
}

type Opportunity = {
  id: string
  slug: string
  title: string
  agency: string
  due_date?: string | null
  set_aside?: string | null
  naics?: string | null
}

type ActionPackage = {
  id: string
  executive_summary: string
  decision: string
  fit_score: number
  fit_rationale: string
  proposal_checklist: string[]
  approval_required: string[]
}

type ProfileFormState = {
  name: string
  capabilities: string
  naics: string
  certifications: string
  location: string
  description: string
  clearanceStatus: string
  smallBusiness: boolean
}

const defaultProfile: ProfileFormState = {
  name: 'Lone Star CyberWorks',
  capabilities: 'cloud migration, cybersecurity, compliance automation',
  naics: '541512, 541519',
  certifications: 'CMMC Level 2',
  location: 'Austin, TX',
  description:
    'Small cybersecurity and cloud migration team focused on federal systems modernization.',
  clearanceStatus: 'none',
  smallBusiness: true,
}

const defaultGoal = 'Find cybersecurity and cloud migration opportunities in the next 90 days.'

function splitList(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function eventLabel(event: TraceEvent) {
  if (event.type === 'tool_called') return `Tool called: ${event.tool}`
  if (event.type === 'tool_returned') return `Tool returned: ${event.tool}`
  if (event.type === 'step_started') return String(event.label ?? 'Step started')
  if (event.type === 'step_completed') return 'Step completed'
  if (event.type === 'opportunity_ranked') {
    return `Ranked ${event.decision} (${event.score ?? 0})`
  }
  if (event.type === 'run_completed') return String(event.summary ?? 'Run completed')
  return event.type.replaceAll('_', ' ')
}

export default function AppConsole() {
  const supabase = useMemo(() => createClient(), [])
  const apiBase = useMemo(() => getApiBase(), [])

  const [token, setToken] = useState<string | null>(null)
  const [profiles, setProfiles] = useState<CompanyProfile[]>([])
  const [selectedProfileId, setSelectedProfileId] = useState('')
  const [profileForm, setProfileForm] = useState<ProfileFormState>(defaultProfile)
  const [goal, setGoal] = useState(defaultGoal)
  const [run, setRun] = useState<AgentRun | null>(null)
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [actionPackage, setActionPackage] = useState<ActionPackage | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function authedFetch(path: string, init: RequestInit = {}) {
    const session =
      token ??
      (await supabase.auth.getSession()).data.session?.access_token ??
      null
    if (!session) throw new Error('Supabase session is missing.')
    const response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${session}`,
        ...init.headers,
      },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new Error(
        typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status})`,
      )
    }
    return response
  }

  const loadProfiles = useCallback(async (currentToken?: string) => {
    const session = currentToken ?? token
    if (!session) return
    const response = await fetch(`${apiBase}/company-profiles`, {
      headers: { Authorization: `Bearer ${session}` },
    })
    if (!response.ok) throw new Error('Could not load company profiles.')
    const rows = (await response.json()) as CompanyProfile[]
    setProfiles(rows)
    setSelectedProfileId((current) => current || rows[0]?.id || '')
  }, [apiBase, token])

  useEffect(() => {
    let cancelled = false
    async function loadSession() {
      const { data } = await supabase.auth.getSession()
      const accessToken = data.session?.access_token ?? null
      if (cancelled) return
      setToken(accessToken)
      if (accessToken) {
        try {
          await loadProfiles(accessToken)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Could not load profiles.')
        }
      }
    }
    void loadSession()
    return () => {
      cancelled = true
    }
  }, [loadProfiles, supabase])

  async function createProfile() {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const response = await authedFetch('/company-profiles', {
        method: 'POST',
        body: JSON.stringify({
          name: profileForm.name,
          description: profileForm.description || null,
          capabilities: splitList(profileForm.capabilities),
          naics_codes: splitList(profileForm.naics),
          certifications: splitList(profileForm.certifications),
          location: profileForm.location || null,
          small_business_status: profileForm.smallBusiness,
          clearance_status: profileForm.clearanceStatus,
          preferred_role: 'either',
        }),
      })
      const created = (await response.json()) as CompanyProfile
      await loadProfiles()
      setSelectedProfileId(created.id)
      setNotice(`Saved ${created.name}.`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save profile.')
    } finally {
      setBusy(false)
    }
  }

  async function startRun() {
    if (!selectedProfileId) {
      setError('Create or select a company profile first.')
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    setEvents([])
    setOpportunities([])
    setActionPackage(null)
    try {
      const response = await authedFetch('/agent-runs', {
        method: 'POST',
        body: JSON.stringify({
          goal,
          profile_id: selectedProfileId,
        }),
      })
      const created = (await response.json()) as AgentRun
      setRun(created)
      setNotice('Michaela run started.')
      void streamRun(created.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start run.')
      setBusy(false)
    }
  }

  async function streamRun(runId: string) {
    try {
      const session =
        token ??
        (await supabase.auth.getSession()).data.session?.access_token ??
        null
      if (!session) throw new Error('Supabase session is missing.')

      const response = await fetch(`${apiBase}/agent-runs/${runId}/stream`, {
        headers: { Authorization: `Bearer ${session}` },
      })
      if (!response.ok || !response.body) throw new Error('Could not open run stream.')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let boundary = buffer.indexOf('\n\n')
        while (boundary !== -1) {
          const chunk = buffer.slice(0, boundary)
          buffer = buffer.slice(boundary + 2)
          const dataLine = chunk
            .split('\n')
            .find((line) => line.startsWith('data: '))
          if (dataLine) {
            const event = JSON.parse(dataLine.slice(6)) as TraceEvent
            setEvents((current) => [...current, event].slice(-80))
            if (event.type === 'run_completed') {
              await refreshRun(runId)
              setBusy(false)
            }
          }
          boundary = buffer.indexOf('\n\n')
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Run stream failed.')
      setBusy(false)
    }
  }

  async function refreshRun(runId: string) {
    const runResponse = await authedFetch(`/agent-runs/${runId}`)
    const nextRun = (await runResponse.json()) as AgentRun
    setRun(nextRun)

    const oppResponse = await authedFetch(`/agent-runs/${runId}/opportunities`)
    setOpportunities((await oppResponse.json()) as Opportunity[])

    if (nextRun.action_package_id) {
      const packageResponse = await authedFetch(`/action-packages/${nextRun.action_package_id}`)
      setActionPackage((await packageResponse.json()) as ActionPackage)
    }
  }

  return (
    <section className="grid gap-5 lg:grid-cols-[390px_1fr]">
      <div className="space-y-5">
        <div className="rounded-[20px] border border-white/80 bg-white/76 p-5 shadow-[0_20px_60px_-44px_rgba(15,23,42,0.5)] backdrop-blur-2xl">
          <div className="flex items-center gap-2 text-sm font-medium text-blue-900">
            <ShieldCheck size={16} aria-hidden />
            Company profile
          </div>
          <div className="mt-4 space-y-3">
            <label className="block">
              <span className="text-xs font-medium text-slate-600">Name</span>
              <input
                value={profileForm.name}
                onChange={(event) =>
                  setProfileForm((current) => ({ ...current, name: event.target.value }))
                }
                className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
              />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-slate-600">Capabilities</span>
              <textarea
                value={profileForm.capabilities}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    capabilities: event.target.value,
                  }))
                }
                rows={2}
                className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="text-xs font-medium text-slate-600">NAICS</span>
                <input
                  value={profileForm.naics}
                  onChange={(event) =>
                    setProfileForm((current) => ({ ...current, naics: event.target.value }))
                  }
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
                />
              </label>
              <label className="block">
                <span className="text-xs font-medium text-slate-600">Clearance</span>
                <select
                  value={profileForm.clearanceStatus}
                  onChange={(event) =>
                    setProfileForm((current) => ({
                      ...current,
                      clearanceStatus: event.target.value,
                    }))
                  }
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
                >
                  <option value="none">None</option>
                  <option value="secret">Secret</option>
                  <option value="top_secret">Top Secret</option>
                </select>
              </label>
            </div>
            <label className="block">
              <span className="text-xs font-medium text-slate-600">Certifications</span>
              <input
                value={profileForm.certifications}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    certifications: event.target.value,
                  }))
                }
                className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
              />
            </label>
            <div className="grid grid-cols-[1fr_auto] items-end gap-3">
              <label className="block">
                <span className="text-xs font-medium text-slate-600">Location</span>
                <input
                  value={profileForm.location}
                  onChange={(event) =>
                    setProfileForm((current) => ({ ...current, location: event.target.value }))
                  }
                  className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
                />
              </label>
              <label className="flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700">
                <input
                  type="checkbox"
                  checked={profileForm.smallBusiness}
                  onChange={(event) =>
                    setProfileForm((current) => ({
                      ...current,
                      smallBusiness: event.target.checked,
                    }))
                  }
                />
                Small
              </label>
            </div>
            <button
              type="button"
              onClick={createProfile}
              disabled={busy}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? <Loader2 size={15} className="animate-spin" aria-hidden /> : null}
              Save profile
            </button>
          </div>
        </div>

        <div className="rounded-[20px] border border-white/80 bg-white/76 p-5 shadow-[0_20px_60px_-44px_rgba(15,23,42,0.5)] backdrop-blur-2xl">
          <div className="flex items-center gap-2 text-sm font-medium text-blue-900">
            <Play size={16} aria-hidden />
            Seeded run
          </div>
          <div className="mt-4 space-y-3">
            <label className="block">
              <span className="text-xs font-medium text-slate-600">Profile</span>
              <select
                value={selectedProfileId}
                onChange={(event) => setSelectedProfileId(event.target.value)}
                className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
              >
                <option value="">Select profile</option>
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
                onChange={(event) => setGoal(event.target.value)}
                rows={3}
                className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
              />
            </label>
            <button
              type="button"
              onClick={startRun}
              disabled={busy}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-full bg-blue-900 px-4 text-sm font-medium text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? <Loader2 size={15} className="animate-spin" aria-hidden /> : <Play size={15} aria-hidden />}
              Start seeded run
            </button>
          </div>
        </div>
      </div>

      <div className="space-y-5">
        {(error || notice) && (
          <div
            className={`flex items-center gap-2 rounded-[18px] border p-4 text-sm ${
              error
                ? 'border-red-200 bg-red-50 text-red-900'
                : 'border-emerald-200 bg-emerald-50 text-emerald-900'
            }`}
            role={error ? 'alert' : 'status'}
          >
            {error ? <AlertCircle size={16} aria-hidden /> : <CheckCircle2 size={16} aria-hidden />}
            {error || notice}
          </div>
        )}

        <div className="rounded-[20px] border border-white/80 bg-white/76 p-5 shadow-[0_20px_60px_-44px_rgba(15,23,42,0.5)] backdrop-blur-2xl">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-blue-900">Run timeline</p>
              <h2 className="text-xl font-semibold tracking-normal">
                {run ? run.status : 'No run started'}
              </h2>
            </div>
            {run && (
              <code className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                {run.id.slice(0, 8)}
              </code>
            )}
          </div>
          <div className="mt-4 max-h-[360px] overflow-auto rounded-2xl border border-slate-200 bg-white">
            {events.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">No events yet.</p>
            ) : (
              <ol className="divide-y divide-slate-100">
                {events.map((event, index) => (
                  <li key={`${event.type}-${index}`} className="p-3">
                    <p className="text-sm font-medium text-slate-900">{eventLabel(event)}</p>
                    <p className="mt-1 text-xs text-slate-500">{event.type}</p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>

        {opportunities.length > 0 && (
          <div className="rounded-[20px] border border-white/80 bg-white/76 p-5 shadow-[0_20px_60px_-44px_rgba(15,23,42,0.5)] backdrop-blur-2xl">
            <p className="text-sm font-medium text-blue-900">Ranked opportunities</p>
            <div className="mt-3 grid gap-3">
              {opportunities.map((opportunity) => (
                <div
                  key={opportunity.id}
                  className="rounded-2xl border border-slate-200 bg-white p-4"
                >
                  <p className="text-sm font-semibold text-slate-950">{opportunity.title}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {opportunity.agency} - {opportunity.naics ?? 'NAICS unknown'} -{' '}
                    {opportunity.due_date ?? 'No due date'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {actionPackage && (
          <div className="rounded-[20px] border border-white/80 bg-white/76 p-5 shadow-[0_20px_60px_-44px_rgba(15,23,42,0.5)] backdrop-blur-2xl">
            <div className="flex items-center gap-2 text-sm font-medium text-blue-900">
              <FileText size={16} aria-hidden />
              Action package
            </div>
            <h2 className="mt-2 text-xl font-semibold tracking-normal">
              {actionPackage.decision.replaceAll('_', ' ')} - {actionPackage.fit_score}
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              {actionPackage.executive_summary}
            </p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Checklist
                </p>
                <ul className="mt-2 space-y-2 text-sm text-slate-700">
                  {actionPackage.proposal_checklist.map((item) => (
                    <li key={item}>- {item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Approval gates
                </p>
                <ul className="mt-2 space-y-2 text-sm text-slate-700">
                  {actionPackage.approval_required.map((item) => (
                    <li key={item}>- {item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
