'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowRight, ChevronRight, Menu, X } from 'lucide-react'
import { NAV } from '../data/copy'
import { cn } from '../lib/cn'

// NEXT_PUBLIC_APP_URL is inlined at build time and is identical on server
// and client, so this can't drift across hydration. Set it per-env.
// Prod-build fallback is the real app origin (app.samrail.com) so a
// missing Vercel env var doesn't ship a localhost <a href> to users.
// Dev fallback is localhost so `next dev` works out of the box.
//
// Defense: an env var entered without the `https://` prefix (e.g.
// "app.samrail.com") is invalid as a URL and the browser would treat
// the resulting href as a same-origin relative path — sending users
// from samrail.com to samrail.com/login (404). Validate the scheme;
// fall back if missing.
function resolveAppUrl(): string {
  const isProd = process.env.NODE_ENV === 'production'
  const fallback = isProd ? 'https://app.samrail.com' : 'http://localhost:3001'
  const raw = process.env.NEXT_PUBLIC_APP_URL?.trim().replace(/\/$/, '')
  if (!raw) return fallback
  if (!/^https?:\/\//i.test(raw)) {
    // Malformed (no scheme). Refuse rather than ship a broken link.
    if (typeof console !== 'undefined') {
      console.warn(
        `[landing] NEXT_PUBLIC_APP_URL="${raw}" missing scheme; using fallback "${fallback}".`,
      )
    }
    return fallback
  }
  return raw
}
const APP_URL = resolveAppUrl()
const SIGN_IN_HREF = `${APP_URL}/login`

function Mark() {
  return (
    <svg viewBox="0 0 32 32" className="w-7 h-7" aria-hidden>
      <rect x="3" y="3" width="26" height="26" rx="7" fill="var(--color-ink)" />
      <path
        d="M10 16 L14 20 L22 12"
        stroke="white"
        strokeWidth="2.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const firstItemRef = useRef<HTMLAnchorElement | null>(null)

  // Close + return focus to the hamburger button. Returning focus is the
  // a11y baseline so keyboard / screen-reader users land where they
  // started rather than at the page root.
  const close = useCallback(() => {
    setOpen(false)
    triggerRef.current?.focus()
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [close])

  // When the mobile menu opens, move focus into the panel. Otherwise
  // keyboard users have to tab through the entire trigger area + page
  // chrome before reaching menu items.
  useEffect(() => {
    if (open) firstItemRef.current?.focus()
  }, [open])

  // Lock body scroll while the mobile menu is open so the page doesn't
  // ghost behind the panel — important now that we've committed harder
  // to the matte body (no scrolled content peeking through).
  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [open])

  return (
    <header className="sticky top-0 z-30 w-full">
      <div className="flex justify-center pt-4 sm:pt-6 px-3 sm:px-4">
        <div className="glass-nav rounded-full pl-2 pr-2 py-2 w-full max-w-[640px] relative">
          <div className="flex items-center gap-3">
            <a
              href="#"
              className="flex items-center gap-2 shrink-0 pl-1 rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
              aria-label="SamRail — back to top"
            >
              <Mark />
              <span className="text-[14px] font-medium tracking-tight text-[var(--color-ink)]">
                SamRail
              </span>
            </a>

            <nav
              className="hidden md:flex items-center gap-5 pl-2"
              aria-label="Primary"
            >
              {NAV.map((n) => (
                <a
                  key={n.href}
                  href={n.href}
                  className="text-[13px] text-[var(--color-ink-muted)] hover:text-[var(--color-ink)] transition-colors rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
                >
                  {n.label}
                </a>
              ))}
            </nav>

            <div className="ml-auto flex items-center gap-1">
              <a
                href={SIGN_IN_HREF}
                className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-[var(--color-ink)] text-white pl-3.5 pr-1 py-1 text-[13px] font-medium hover:bg-[#1e293b] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
              >
                Sign in
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-white/15">
                  <ArrowRight size={12} strokeWidth={2.25} aria-hidden />
                </span>
              </a>

              <button
                ref={triggerRef}
                type="button"
                aria-label={open ? 'Close menu' : 'Open menu'}
                aria-expanded={open}
                aria-controls="mobile-menu"
                onClick={() => (open ? close() : setOpen(true))}
                className="md:hidden w-8 h-8 inline-flex items-center justify-center rounded-full text-[var(--color-ink)] hover:bg-white/40 active:bg-white/60 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
              >
                {open ? <X size={16} /> : <Menu size={16} />}
              </button>
            </div>
          </div>

          {open && (
            <div
              id="mobile-menu"
              /* Inline `position: absolute` to defeat the
               * `.glass-strong { position: relative }` base rule —
               * which otherwise forces this menu into the navbar's
               * normal flow and inflates the pill to ~247px tall. */
              style={{ position: 'absolute' }}
              className="md:hidden glass-strong left-0 right-0 top-full mt-3 rounded-[var(--radius-card)] p-2"
            >
              <nav className="flex flex-col gap-0.5" aria-label="Mobile">
                {NAV.map((n, i) => (
                  <a
                    key={n.href}
                    ref={i === 0 ? firstItemRef : undefined}
                    href={n.href}
                    onClick={close}
                    className={cn(
                      'group flex items-center justify-between h-12 px-4 rounded-xl',
                      'text-[15px] font-medium text-[var(--color-ink)]',
                      'hover:bg-white/50 active:bg-white/65 transition-colors',
                      'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]',
                    )}
                  >
                    <span>{n.label}</span>
                    <ChevronRight
                      size={16}
                      strokeWidth={1.75}
                      className="text-[var(--color-ink-subtle)] group-hover:text-[var(--color-ink)] transition-colors"
                      aria-hidden
                    />
                  </a>
                ))}
                <a
                  href={SIGN_IN_HREF}
                  onClick={close}
                  className={cn(
                    'flex items-center justify-between h-12 px-4 rounded-xl',
                    'text-[15px] font-medium text-[var(--color-ink)]',
                    'hover:bg-white/50 active:bg-white/65 transition-colors',
                    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]',
                  )}
                >
                  <span>Sign in</span>
                  <ChevronRight
                    size={16}
                    strokeWidth={1.75}
                    className="text-[var(--color-ink-subtle)]"
                    aria-hidden
                  />
                </a>
              </nav>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
