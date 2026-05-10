'use client'

import { Loader2 } from 'lucide-react'
import { useFormStatus } from 'react-dom'

function GoogleGlyph() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 18 18"
      aria-hidden
      className="shrink-0"
    >
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.81 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.93v2.33A8.99 8.99 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72A5.41 5.41 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.95H.93A8.99 8.99 0 0 0 0 9c0 1.45.35 2.83.93 4.05l3.04-2.33z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.43 1.34l2.58-2.58A8.99 8.99 0 0 0 9 0 8.99 8.99 0 0 0 .93 4.95l3.04 2.33C4.68 5.16 6.66 3.58 9 3.58z"
      />
    </svg>
  )
}

export function GoogleButton() {
  const { pending } = useFormStatus()
  return (
    <button
      type="submit"
      disabled={pending}
      className="inline-flex h-11 w-full items-center justify-center gap-2.5 rounded-full border border-[var(--color-canvas-border)] bg-white px-4 text-[14px] font-medium text-[var(--color-ink)] transition hover:bg-[var(--color-canvas-subtle)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-70"
    >
      {pending ? (
        <Loader2 size={15} className="animate-spin" aria-hidden />
      ) : (
        <GoogleGlyph />
      )}
      <span>{pending ? 'Redirecting…' : 'Continue with Google'}</span>
    </button>
  )
}
