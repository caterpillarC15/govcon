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
      className={`rounded-[20px] border border-white/80 bg-white/76 p-5 shadow-[0_20px_60px_-44px_rgba(15,23,42,0.5)] backdrop-blur-2xl ${className}`}
    >
      {children}
    </div>
  )
}
