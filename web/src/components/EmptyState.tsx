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
    <div className="flex flex-col items-center justify-center gap-3 rounded-[20px] border border-dashed border-slate-200 bg-white/40 p-10 text-center">
      {icon ? <div className="text-blue-900">{icon}</div> : null}
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      {description ? (
        <p className="max-w-sm text-sm leading-6 text-slate-600">{description}</p>
      ) : null}
      {action}
    </div>
  )
}
