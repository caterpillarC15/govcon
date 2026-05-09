'use client'

import { useState, type FormEvent } from 'react'
import { ArrowRight, Check } from 'lucide-react'
import { Button, GlassCard } from '../ui/Primitives'

/**
 * Final CTA. The MVP has no waitlist endpoint wired (PRD §6 non-goals
 * list "Real email sending"), so submission is acknowledged locally —
 * replace with a POST when one exists. Kept compact so the page does
 * not have two hero-sized CTAs.
 */
export default function Waitlist() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!email || !email.includes('@')) return
    setSubmitted(true)
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
              Run a real capture against your{' '}
              <span
                style={{ fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontWeight: 400 }}
              >
                profile
              </span>
              .
            </h2>
            <p className="mt-1.5 text-[12.5px] text-[var(--color-ink-subtle)]">
              Profile data stays in your tenant. No CUI / classified material.
            </p>
          </div>

          {submitted ? (
            <div className="inline-flex items-center justify-center gap-2 glass rounded-full px-4 py-2 text-[13.5px] text-[var(--color-ink)] shrink-0">
              <Check size={14} className="text-[var(--color-decision-strong)]" aria-hidden />
              You’re on the list.
            </div>
          ) : (
            <form
              onSubmit={onSubmit}
              className="flex flex-col sm:flex-row gap-2 md:shrink-0 md:w-[380px]"
              aria-describedby="waitlist-help"
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
                className="flex-1 h-11 px-4 rounded-full glass-subtle text-[14px] text-[var(--color-ink)] placeholder:text-[var(--color-ink-subtle)] outline-none focus:ring-2 focus:ring-[var(--color-accent)]/40 focus:bg-white/85"
              />
              <Button type="submit" variant="primary" size="md">
                Request access
                <ArrowRight size={14} strokeWidth={2} aria-hidden />
              </Button>
              <span id="waitlist-help" className="sr-only">
                We'll email when private beta opens. No spam.
              </span>
            </form>
          )}
        </GlassCard>
      </div>
    </section>
  )
}
