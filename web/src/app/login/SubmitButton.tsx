'use client'

import { ArrowRight, Loader2 } from 'lucide-react'
import { useFormStatus } from 'react-dom'

export function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus()
  return (
    <button
      type="submit"
      disabled={pending}
      className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-full bg-[var(--color-ink)] px-5 text-[14px] font-medium text-white transition hover:bg-[#1e293b] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-70"
    >
      {pending ? (
        <Loader2 size={15} className="animate-spin" aria-hidden />
      ) : null}
      <span>{pending ? 'Sending…' : label}</span>
      {!pending ? (
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/15">
          <ArrowRight size={12} strokeWidth={2.25} aria-hidden />
        </span>
      ) : null}
    </button>
  )
}
