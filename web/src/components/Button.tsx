import Link from 'next/link'
import type { ComponentProps, ReactNode } from 'react'
import { cn } from '@/lib/cn'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md'

const base =
  'inline-flex items-center justify-center gap-2 rounded-full font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]'

const variants: Record<Variant, string> = {
  primary:
    'bg-[var(--color-ink)] text-white hover:bg-[#1e293b] active:bg-[#020617] shadow-[0_1px_2px_rgba(15,23,42,0.18),0_8px_24px_-12px_rgba(15,23,42,0.45)]',
  secondary:
    'border border-[var(--color-canvas-border)] bg-white/80 text-[var(--color-ink)] hover:bg-white',
  ghost:
    'text-[var(--color-ink-muted)] hover:bg-white/50 hover:text-[var(--color-ink)]',
  danger:
    'border border-rose-200 bg-rose-50 text-rose-900 hover:border-rose-300 hover:bg-rose-100',
}

const sizes: Record<Size, string> = {
  sm: 'h-9 px-3 text-[12.5px]',
  md: 'h-10 px-4 text-[13.5px]',
}

type CommonProps = {
  variant?: Variant
  size?: Size
  className?: string
  children: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  ...rest
}: CommonProps & ComponentProps<'button'>) {
  return (
    <button
      {...rest}
      className={cn(base, variants[variant], sizes[size], className)}
    />
  )
}

export function ButtonLink({
  variant = 'primary',
  size = 'md',
  className,
  href,
  ...rest
}: CommonProps & { href: string } & Omit<ComponentProps<'a'>, 'href'>) {
  return (
    <Link
      href={href}
      {...rest}
      className={cn(base, variants[variant], sizes[size], className)}
    />
  )
}
