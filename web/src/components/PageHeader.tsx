import type { ReactNode } from 'react'

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: string
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? (
          <p className="text-[11.5px] font-medium uppercase tracking-[0.14em] text-[var(--color-ink-muted)]">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="mt-1 text-[26px] font-semibold leading-[1.1] tracking-[-0.01em] text-[var(--color-ink)]">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-1 text-[14px] leading-[1.55] text-[var(--color-ink-muted)]">
            {subtitle}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </header>
  )
}
