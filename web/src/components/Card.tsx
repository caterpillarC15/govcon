import type { ReactNode } from 'react'

export function Card({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={`glass-strong rounded-[var(--radius-card)] p-5 ${className}`}
    >
      {children}
    </div>
  )
}
