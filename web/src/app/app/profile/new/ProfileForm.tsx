'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { api, ApiError } from '@/lib/api'

type FormState = {
  name: string
  capabilities: string
  naics: string
  certifications: string
  location: string
  description: string
  clearanceStatus: string
  smallBusiness: boolean
}

const initialForm: FormState = {
  name: '',
  capabilities: '',
  naics: '',
  certifications: '',
  location: '',
  description: '',
  clearanceStatus: 'none',
  smallBusiness: true,
}

function splitList(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function ProfileForm() {
  const router = useRouter()
  const supabase = createClient()
  const [form, setForm] = useState<FormState>(initialForm)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const session = (await supabase.auth.getSession()).data.session
      if (!session) {
        setError('Session expired. Sign in again.')
        return
      }
      const created = await api.createCompanyProfile(session.access_token, {
        name: form.name.trim(),
        description: form.description || null,
        capabilities: splitList(form.capabilities),
        naics_codes: splitList(form.naics),
        certifications: splitList(form.certifications),
        location: form.location || null,
        small_business_status: form.smallBusiness,
        clearance_status: form.clearanceStatus,
        preferred_role: 'either',
      })
      router.push(`/app/profile/${created.id}`)
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Could not save profile.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field label="Name" required>
        <input
          value={form.name}
          onChange={(e) => setForm((c) => ({ ...c, name: e.target.value }))}
          required
          className={inputCls}
        />
      </Field>
      <Field label="Capabilities (comma-separated)">
        <textarea
          value={form.capabilities}
          onChange={(e) =>
            setForm((c) => ({ ...c, capabilities: e.target.value }))
          }
          rows={2}
          className={inputCls}
        />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="NAICS codes (comma-separated)">
          <input
            value={form.naics}
            onChange={(e) => setForm((c) => ({ ...c, naics: e.target.value }))}
            className={inputCls}
          />
        </Field>
        <Field label="Clearance">
          <select
            value={form.clearanceStatus}
            onChange={(e) =>
              setForm((c) => ({ ...c, clearanceStatus: e.target.value }))
            }
            className={inputCls}
          >
            <option value="none">None</option>
            <option value="secret">Secret</option>
            <option value="top_secret">Top Secret</option>
          </select>
        </Field>
      </div>
      <Field label="Certifications (comma-separated)">
        <input
          value={form.certifications}
          onChange={(e) =>
            setForm((c) => ({ ...c, certifications: e.target.value }))
          }
          className={inputCls}
        />
      </Field>
      <div className="grid grid-cols-[1fr_auto] items-end gap-3">
        <Field label="Location">
          <input
            value={form.location}
            onChange={(e) =>
              setForm((c) => ({ ...c, location: e.target.value }))
            }
            className={inputCls}
          />
        </Field>
        <label className="flex h-10 items-center gap-2 rounded-xl border border-[var(--color-canvas-border)] bg-white px-3 text-xs font-medium text-[var(--color-ink)]">
          <input
            type="checkbox"
            checked={form.smallBusiness}
            onChange={(e) =>
              setForm((c) => ({ ...c, smallBusiness: e.target.checked }))
            }
          />
          Small business
        </label>
      </div>
      <Field label="Description">
        <textarea
          value={form.description}
          onChange={(e) =>
            setForm((c) => ({ ...c, description: e.target.value }))
          }
          rows={3}
          className={inputCls}
        />
      </Field>
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
        className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-full bg-[var(--color-ink)] px-4 text-sm font-medium text-white transition hover:bg-[#1e293b] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {busy ? <Loader2 size={15} className="animate-spin" aria-hidden /> : null}
        {busy ? 'Saving…' : 'Create profile'}
      </button>
    </form>
  )
}

const inputCls =
  'mt-1 w-full rounded-xl border border-[var(--color-canvas-border)] bg-white px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent-subtle)]'

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-[var(--color-ink-muted)]">
        {label}
        {required ? ' *' : ''}
      </span>
      {children}
    </label>
  )
}
