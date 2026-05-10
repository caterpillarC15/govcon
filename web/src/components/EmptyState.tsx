import type { ReactNode } from 'react'

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="glass-subtle flex flex-col items-center justify-center gap-3 rounded-[var(--radius-card)] p-10 text-center">
      {icon ? (
        <div className="text-[var(--color-accent)]" aria-hidden>
          {icon}
        </div>
      ) : null}
      <h3 className="text-[15px] font-semibold text-[var(--color-ink)]">
        {title}
      </h3>
      {description ? (
        <p className="max-w-sm text-[13.5px] leading-[1.6] text-[var(--color-ink-muted)]">
          {description}
        </p>
      ) : null}
      {action}
    </div>
  )
}
