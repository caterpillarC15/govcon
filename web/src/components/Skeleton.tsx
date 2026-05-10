export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-xl bg-slate-200/60 ${className}`}
      aria-hidden
    />
  )
}
