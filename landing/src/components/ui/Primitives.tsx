import type { ReactNode, ButtonHTMLAttributes, AnchorHTMLAttributes } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'
type ButtonSize = 'md' | 'sm' | 'lg'

type ButtonBase = {
  variant?: ButtonVariant
  size?: ButtonSize
  children: ReactNode
}

const buttonClass = (variant: ButtonVariant, size: ButtonSize) => {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-full font-medium transition-[background-color,box-shadow,transform] disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]'
  const sizes: Record<ButtonSize, string> = {
    sm: 'h-8 px-3 text-[13px]',
    md: 'h-10 px-4 text-[14px]',
    lg: 'h-12 px-6 text-[15px]',
  }
  const variants: Record<ButtonVariant, string> = {
    primary:
      'bg-[var(--color-ink)] text-white hover:bg-[#1e293b] active:bg-[#020617] shadow-[0_1px_2px_rgba(15,23,42,0.16),0_8px_24px_-12px_rgba(15,23,42,0.4)]',
    secondary:
      'glass-subtle text-[var(--color-ink)] hover:bg-white/70',
    ghost: 'bg-transparent text-[var(--color-ink-muted)] hover:text-[var(--color-ink)] hover:bg-white/40',
  }
  return [base, sizes[size], variants[variant]].join(' ')
}

export function Button({
  variant = 'primary',
  size = 'md',
  children,
  className = '',
  ...rest
}: ButtonBase & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className={`${buttonClass(variant, size)} ${className}`} {...rest}>
      {children}
    </button>
  )
}

export function LinkButton({
  variant = 'primary',
  size = 'md',
  children,
  className = '',
  ...rest
}: ButtonBase & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return (
    <a className={`${buttonClass(variant, size)} ${className}`} {...rest}>
      {children}
    </a>
  )
}

type Decision = 'strong_pursue' | 'pursue' | 'maybe' | 'reject'
type Status = 'met' | 'missing' | 'unclear' | 'na'
type BadgeTone = Decision | Status | 'neutral' | 'accent' | 'live'

const toneClass: Record<BadgeTone, string> = {
  strong_pursue: 'bg-emerald-50 text-[var(--color-decision-strong)] ring-emerald-200/70',
  pursue: 'bg-blue-50 text-[var(--color-decision-pursue)] ring-blue-200/70',
  maybe: 'bg-amber-50 text-[var(--color-decision-maybe)] ring-amber-200/70',
  reject: 'bg-red-50 text-[var(--color-decision-reject)] ring-red-200/70',
  met: 'bg-emerald-50 text-[var(--color-status-met)] ring-emerald-200/70',
  missing: 'bg-red-50 text-[var(--color-status-missing)] ring-red-200/70',
  unclear: 'bg-amber-50 text-[var(--color-status-unclear)] ring-amber-200/70',
  na: 'bg-slate-50 text-[var(--color-status-na)] ring-slate-200/70',
  neutral: 'bg-white text-[var(--color-ink-muted)] ring-[var(--color-paper-line)]',
  accent: 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)] ring-blue-200/70',
  live: 'bg-emerald-50 text-[var(--color-decision-strong)] ring-emerald-200/70',
}

export function Badge({
  tone = 'neutral',
  children,
  mono = false,
}: {
  tone?: BadgeTone
  children: ReactNode
  mono?: boolean
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11.5px] font-medium ring-1 ring-inset ${toneClass[tone]} ${
        mono ? 'font-mono tracking-tight' : ''
      }`}
    >
      {children}
    </span>
  )
}

type SurfaceVariant = 'glass' | 'glass-strong' | 'glass-subtle' | 'paper'

/**
 * Surface card with shared layered glass material from globals.css.
 * `glass-strong` for primary cards + final CTA; `glass` for ambient
 * surfaces; `glass-subtle` for inner tiles + pills; `paper` for
 * legacy non-glass tiles inside cards (use sparingly).
 */
export function GlassCard({
  children,
  className = '',
  variant = 'paper',
}: {
  children: ReactNode
  className?: string
  variant?: SurfaceVariant
}) {
  return (
    <div className={`${variant} rounded-[var(--radius-card)] ${className}`}>{children}</div>
  )
}

/**
 * Compact glass pill — status labels, beta tags, trust items.
 * Always include a text label (no color-only meaning).
 */
export function GlassPill({
  children,
  dot,
  className = '',
}: {
  children: ReactNode
  /** Optional leading colored dot for liveness/status. */
  dot?: 'live' | 'neutral'
  className?: string
}) {
  const dotColor = dot === 'live' ? 'bg-emerald-500' : 'bg-[var(--color-ink-subtle)]'
  return (
    <span
      className={`glass-subtle inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[12px] tracking-tight text-[var(--color-ink-muted)] ${className}`}
    >
      {dot && <span className={`inline-block w-1.5 h-1.5 rounded-full ${dotColor}`} aria-hidden />}
      {children}
    </span>
  )
}

/**
 * Inner tile rendered on top of a glass card — uses .glass-subtle so
 * the material reads as glass-on-glass instead of glass-on-paper.
 */
export function InnerTile({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`glass-subtle rounded-[var(--radius-tile)] ${className}`}>{children}</div>
  )
}
