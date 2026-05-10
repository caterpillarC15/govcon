'use client'

import Link from 'next/link'
import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <main className="min-h-screen bg-[#f7f8fb] text-[var(--color-ink)]">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-6 py-12">
        <div className="rounded-[28px] border border-white/80 bg-white/72 p-7 shadow-[0_24px_70px_-36px_rgba(15,23,42,0.42)] backdrop-blur-2xl">
          <p className="text-sm font-medium text-rose-700">Something broke</p>
          <h1 className="mt-3 text-2xl font-semibold tracking-normal">
            We hit an unexpected error
          </h1>
          <p className="mt-3 text-sm leading-6 text-[var(--color-ink-muted)]">
            Try again, or head back to the dashboard. If this keeps happening,
            email{' '}
            <a
              className="font-medium text-[var(--color-accent)] underline-offset-4 hover:underline"
              href="mailto:support@samrail.com"
            >
              support@samrail.com
            </a>
            {error.digest ? ` and quote error id ${error.digest}.` : '.'}
          </p>
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              onClick={() => reset()}
              className="inline-flex h-10 items-center gap-2 rounded-full bg-[var(--color-ink)] px-4 text-sm font-medium text-white transition hover:bg-[#1e293b]"
            >
              Try again
            </button>
            <Link
              href="/app"
              className="inline-flex h-10 items-center gap-2 rounded-full border border-[var(--color-canvas-border)] bg-white px-4 text-sm font-medium text-[var(--color-ink)] transition hover:border-[var(--color-canvas-border)] hover:bg-slate-50"
            >
              Dashboard
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
