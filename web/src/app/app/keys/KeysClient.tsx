'use client'

import { useState } from 'react'
import { Copy, KeyRound, Loader2, Trash2 } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { api, ApiError } from '@/lib/api'
import { Card } from '@/components/Card'
import type { ApiKey, ApiKeyMint } from '@/lib/types'

export function KeysClient({ initial }: { initial: ApiKey[] }) {
  const supabase = createClient()
  const [keys, setKeys] = useState<ApiKey[]>(initial)
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [justMinted, setJustMinted] = useState<ApiKeyMint | null>(null)

  async function withToken(): Promise<string | null> {
    const session = (await supabase.auth.getSession()).data.session
    if (!session) {
      setError('Session expired. Sign in again.')
      return null
    }
    return session.access_token
  }

  async function refresh(token: string) {
    try {
      setKeys(await api.listApiKeys(token))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Refresh failed.')
    }
  }

  async function mint(event: React.FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    setError('')
    try {
      const token = await withToken()
      if (!token) return
      const minted = await api.mintApiKey(token, name.trim())
      setJustMinted(minted)
      setName('')
      await refresh(token)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Mint failed.')
    } finally {
      setBusy(false)
    }
  }

  async function revoke(id: string) {
    if (
      !confirm(
        'Revoke this key? Calls using it will start failing immediately.',
      )
    )
      return
    setBusy(true)
    setError('')
    try {
      const token = await withToken()
      if (!token) return
      await api.revokeApiKey(token, id)
      await refresh(token)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Revoke failed.')
    } finally {
      setBusy(false)
    }
  }

  const activeCount = keys.filter((k) => !k.revoked_at).length

  return (
    <div className="space-y-6">
      {justMinted ? (
        <Card className="border-emerald-200 bg-emerald-50/80">
          <p className="text-sm font-medium text-emerald-900">
            New key minted — copy it now. We can&apos;t show it again.
          </p>
          <pre className="mt-3 overflow-auto rounded-2xl border border-emerald-200 bg-white p-3 text-xs text-emerald-900">
            {justMinted.plaintext_key}
          </pre>
          <div className="mt-3 flex gap-3">
            <button
              type="button"
              onClick={() => {
                void navigator.clipboard.writeText(justMinted.plaintext_key)
              }}
              className="inline-flex h-9 items-center gap-2 rounded-full bg-emerald-700 px-3 text-xs font-medium text-white transition hover:bg-emerald-600"
            >
              <Copy size={13} aria-hidden /> Copy
            </button>
            <button
              type="button"
              onClick={() => setJustMinted(null)}
              className="inline-flex h-9 items-center gap-2 rounded-full border border-emerald-200 bg-white px-3 text-xs font-medium text-emerald-900 transition hover:border-emerald-300"
            >
              I&apos;ve saved it
            </button>
          </div>
        </Card>
      ) : null}

      <Card>
        <form
          onSubmit={mint}
          className="flex flex-col gap-2 sm:flex-row sm:items-end"
        >
          <label className="block flex-1">
            <span className="text-xs font-medium text-slate-600">
              New key name
            </span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. claude-desktop, prod-orchestrator"
              maxLength={120}
              className="mt-1 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-800 focus:ring-2 focus:ring-blue-800/20"
            />
          </label>
          <button
            type="submit"
            disabled={busy || !name.trim()}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-slate-950 px-4 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy ? (
              <Loader2 size={15} className="animate-spin" aria-hidden />
            ) : (
              <KeyRound size={15} aria-hidden />
            )}
            Mint
          </button>
        </form>
        {error ? (
          <p
            className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-900"
            role="alert"
          >
            {error}
          </p>
        ) : null}
      </Card>

      <Card>
        <p className="text-sm font-medium text-blue-900">
          Active keys ({activeCount})
        </p>
        {keys.length === 0 ? (
          <p className="mt-3 text-sm text-slate-600">
            No keys yet. Mint one to start calling /api/v1/tools/&lt;name&gt;.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {keys.map((key) => (
              <li
                key={key.id}
                className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3"
              >
                <div>
                  <p className="text-sm font-semibold text-slate-950">
                    {key.name}
                  </p>
                  <p className="mt-1 font-mono text-xs text-slate-500">
                    {key.prefix}…{key.revoked_at ? ' · revoked' : ''}
                  </p>
                </div>
                {!key.revoked_at ? (
                  <button
                    type="button"
                    onClick={() => void revoke(key.id)}
                    disabled={busy}
                    className="inline-flex h-8 items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-3 text-xs font-medium text-rose-900 transition hover:border-rose-300 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Trash2 size={12} aria-hidden /> Revoke
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
