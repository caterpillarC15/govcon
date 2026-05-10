'use client'

import { useState, type FormEvent } from 'react'
import { ArrowRight, Check } from 'lucide-react'
import { Button, GlassCard } from '../ui/Primitives'

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000').replace(
  /\/$/,
  '',
)

export default function Waitlist() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>(
    'idle',
  )
  const [message, setMessage] = useState('')

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const normalizedEmail = email.trim().toLowerCase()
    if (!normalizedEmail || !normalizedEmail.includes('@')) return

    setStatus('loading')
    setMessage('')

    try {
      const response = await fetch(`${API_BASE}/waitlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: normalizedEmail,
          source: 'landing',
        }),
      })

      if (!response.ok) {
        const body = await response.json().catch(() => null)
        const detail =
          typeof body?.detail === 'string' ? body.detail : 'Could not save that email.'
        throw new Error(detail)
      }

      const body = (await response.json()) as { already_registered?: boolean }
      setStatus('success')
      setMessage(
        body.already_registered
          ? "You're already on the private beta list."
          : "You're on the private beta list.",
      )
    } catch (error) {
      setStatus('error')
      setMessage(error instanceof Error ? error.message : 'Could not save that email.')
    }
  }

  return (
    <section id="waitlist" className="relative w-full" aria-labelledby="waitlist-heading">
      <div className="mx-auto max-w-[860px] px-5 sm:px-8 pb-16 sm:pb-20">
        <GlassCard
          variant="glass-strong"
          className="px-6 sm:px-8 py-7 sm:py-8 flex flex-col md:flex-row md:items-center md:justify-between gap-5"
        >
          <div className="text-center md:text-left">
            <h2
              id="waitlist-heading"
              className="text-[var(--color-ink)]"
              style={{
                fontSize: 'clamp(20px, 2.4vw, 24px)',
                lineHeight: 1.2,
                letterSpacing: '-0.02em',
                fontWeight: 600,
              }}
            >
              Run a real bid review against your{' '}
              <span
                style={{ fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontWeight: 400 }}
              >
                profile
              </span>
              .
            </h2>
            <p className="mt-1.5 text-[12.5px] text-[var(--color-ink-subtle)]">
              We&apos;ll follow up before any profile or solicitation review. No CUI /
              classified material.
            </p>
          </div>

          {status === 'success' ? (
            <div
              className="inline-flex items-center justify-center gap-2 glass rounded-full px-4 py-2 text-[13.5px] text-[var(--color-ink)] shrink-0"
              role="status"
            >
              <Check size={14} className="text-[var(--color-decision-strong)]" aria-hidden />
              {message}
            </div>
          ) : (
            <form
              onSubmit={onSubmit}
              className="flex flex-col sm:flex-row gap-2 md:shrink-0 md:w-[380px]"
              aria-describedby="waitlist-help waitlist-status"
            >
              <label htmlFor="waitlist-email" className="sr-only">
                Work email
              </label>
              <input
                id="waitlist-email"
                type="email"
                required
                placeholder="you@yourcompany.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={status === 'loading'}
                className="flex-1 h-11 px-4 rounded-full glass-subtle text-[14px] text-[var(--color-ink)] placeholder:text-[var(--color-ink-subtle)] outline-none focus:ring-2 focus:ring-[var(--color-accent)]/40 focus:bg-white/85"
              />
              <Button type="submit" variant="primary" size="md" disabled={status === 'loading'}>
                {status === 'loading' ? 'Saving...' : 'Request access'}
                <ArrowRight size={14} strokeWidth={2} aria-hidden />
              </Button>
              <span id="waitlist-help" className="sr-only">
                We'll email when private beta opens. No spam.
              </span>
              <span
                id="waitlist-status"
                className="sr-only"
                role={status === 'error' ? 'alert' : 'status'}
                aria-live="polite"
              >
                {message}
              </span>
              {status === 'error' && (
                <p className="sm:col-span-2 text-center sm:text-left text-[12.5px] text-[var(--color-decision-reject)]">
                  {message}
                </p>
              )}
            </form>
          )}
        </GlassCard>
      </div>
    </section>
  )
}
