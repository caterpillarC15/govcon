import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export const inputClass =
  'mt-1.5 h-10 w-full rounded-xl border border-[var(--color-canvas-border)] bg-white/85 px-3 text-[13.5px] text-[var(--color-ink)] outline-none transition placeholder:text-[var(--color-ink-subtle)] focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent-subtle)]'

export const textareaClass = cn(inputClass, 'h-auto py-2 leading-[1.5]')

export function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string
  required?: boolean
  hint?: string
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="text-[12.5px] font-medium text-[var(--color-ink)]">
        {label}
        {required ? <span className="text-rose-700"> *</span> : null}
      </span>
      {children}
      {hint ? (
        <span className="mt-1 block text-[11.5px] text-[var(--color-ink-subtle)]">
          {hint}
        </span>
      ) : null}
    </label>
  )
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="rounded-2xl border border-red-200/70 bg-red-50/85 px-4 py-3 text-[13px] leading-[1.55] text-red-900"
    >
      {message}
    </p>
  )
}
