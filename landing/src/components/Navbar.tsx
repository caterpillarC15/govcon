'use client'

import { useEffect, useState } from 'react'
import { ArrowRight, Menu, X } from 'lucide-react'
import { NAV } from '../data/copy'

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

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <header className="sticky top-0 z-30 w-full">
      <div className="flex justify-center pt-4 sm:pt-6 px-3 sm:px-4">
        <div className="glass-nav rounded-full pl-2 pr-2 py-2 w-full max-w-[640px] relative">
          <div className="flex items-center gap-3">
            <a
              href="#"
              className="flex items-center gap-2 shrink-0 pl-1 rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
              aria-label="GovCapture — back to top"
            >
              <Mark />
              <span className="text-[14px] font-medium tracking-tight text-[var(--color-ink)]">
                GovCapture
              </span>
            </a>

            <nav className="hidden md:flex items-center gap-5 pl-2" aria-label="Primary">
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
                href="#waitlist"
                className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-[var(--color-ink)] text-white pl-3.5 pr-1 py-1 text-[13px] font-medium hover:bg-[#1e293b] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
              >
                Request access
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-white/15">
                  <ArrowRight size={12} strokeWidth={2.25} />
                </span>
              </a>

              <button
                type="button"
                aria-label={open ? 'Close menu' : 'Open menu'}
                aria-expanded={open}
                aria-controls="mobile-menu"
                onClick={() => setOpen((v) => !v)}
                className="md:hidden w-8 h-8 inline-flex items-center justify-center rounded-full text-[var(--color-ink)] hover:bg-white/40 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
              >
                {open ? <X size={16} /> : <Menu size={16} />}
              </button>
            </div>
          </div>

          {open && (
            <div
              id="mobile-menu"
              className="md:hidden glass-strong absolute left-0 right-0 top-full mt-2 rounded-[var(--radius-card)] p-2"
            >
              <nav className="flex flex-col" aria-label="Mobile">
                {NAV.map((n) => (
                  <a
                    key={n.href}
                    href={n.href}
                    onClick={() => setOpen(false)}
                    className="px-3 py-3 text-[15px] text-[var(--color-ink)] border-b border-[var(--color-paper-line)] last:border-b-0"
                  >
                    {n.label}
                  </a>
                ))}
                <a
                  href="#waitlist"
                  onClick={() => setOpen(false)}
                  className="mt-2 inline-flex items-center justify-center gap-2 h-11 rounded-full bg-[var(--color-ink)] text-white text-[14px] font-medium"
                >
                  Request access
                  <ArrowRight size={14} strokeWidth={2} />
                </a>
              </nav>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
