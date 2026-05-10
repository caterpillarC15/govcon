import Link from 'next/link'
import type { ReactNode } from 'react'
import { Mark } from '@/components/Mark'

export function LegalShell({ children }: { children: ReactNode }) {
  return (
    <main className="relative min-h-screen w-full">
      <header className="mx-auto flex w-full max-w-[760px] items-center justify-between px-5 pt-6 sm:px-8">
        <Link
          href="/"
          aria-label="GovCon Bid Desk — home"
          className="inline-flex items-center gap-2 rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
        >
          <Mark />
          <span className="text-[14px] font-medium tracking-tight text-[var(--color-ink)]">
            GovCon Bid Desk
          </span>
        </Link>
        <Link
          href="/login"
          className="text-[13px] font-medium text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]"
        >
          Sign in
        </Link>
      </header>
      <div className="mx-auto w-full max-w-[760px] px-5 py-10 sm:px-8">
        <article className="glass-strong rounded-[var(--radius-card)] p-8 [&_h2]:mt-7 [&_h2]:text-[18px] [&_h2]:font-semibold [&_h2]:text-[var(--color-ink)] [&_p]:mt-3 [&_p]:text-[14px] [&_p]:leading-[1.65] [&_p]:text-[var(--color-ink-muted)]">
          {children}
        </article>
      </div>
    </main>
  )
}
