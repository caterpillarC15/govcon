import type {
  ReactNode,
  ButtonHTMLAttributes,
  AnchorHTMLAttributes,
  HTMLAttributes,
} from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/cn'

/* ------- Button + LinkButton ----------------------------------------- */

const buttonVariants = cva(
  cn(
    'inline-flex items-center justify-center gap-2 rounded-full font-medium',
    'transition-[background-color,box-shadow,transform]',
    'disabled:opacity-50 disabled:pointer-events-none',
    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]',
  ),
  {
    variants: {
      variant: {
        primary:
          'bg-[var(--color-ink)] text-white hover:bg-[#1e293b] active:bg-[#020617] shadow-[0_1px_2px_rgba(15,23,42,0.16),0_8px_24px_-12px_rgba(15,23,42,0.4)]',
        secondary: 'glass-subtle text-[var(--color-ink)] hover:bg-white/70',
        ghost:
          'bg-transparent text-[var(--color-ink-muted)] hover:text-[var(--color-ink)] hover:bg-white/40',
      },
      size: {
        sm: 'h-8 px-3 text-[13px]',
        md: 'h-10 px-4 text-[14px]',
        lg: 'h-12 px-6 text-[15px]',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
)

type ButtonVariantProps = VariantProps<typeof buttonVariants>

export function Button({
  variant,
  size,
  className,
  children,
  ...rest
}: ButtonVariantProps & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className={cn(buttonVariants({ variant, size }), className)} {...rest}>
      {children}
    </button>
  )
}

export function LinkButton({
  variant,
  size,
  className,
  children,
  ...rest
}: ButtonVariantProps & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return (
    <a className={cn(buttonVariants({ variant, size }), className)} {...rest}>
      {children}
    </a>
  )
}

/* ------- Badge ------------------------------------------------------- */

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11.5px] font-medium ring-1 ring-inset',
  {
    variants: {
      tone: {
        strong_pursue:
          'bg-emerald-50 text-[var(--color-decision-strong)] ring-emerald-200/70',
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
      },
      mono: {
        true: 'font-mono tracking-tight',
        false: '',
      },
    },
    defaultVariants: {
      tone: 'neutral',
      mono: false,
    },
  },
)

type BadgeVariantProps = VariantProps<typeof badgeVariants>

export function Badge({
  tone,
  mono,
  children,
}: BadgeVariantProps & { children: ReactNode }) {
  return <span className={badgeVariants({ tone, mono })}>{children}</span>
}

/* ------- Glass surfaces --------------------------------------------- */

type SurfaceVariant = 'glass' | 'glass-strong' | 'glass-subtle' | 'paper'

/**
 * Surface card with shared layered glass material from globals.css.
 * `glass-strong` for primary cards + final CTA; `glass` for ambient
 * surfaces; `glass-subtle` for inner tiles + pills; `paper` for
 * legacy non-glass tiles inside cards (use sparingly).
 *
 * Forwards arbitrary div attributes (style, role, etc.) so callers
 * can layer per-card behavior like staggered animation-delay.
 */
export function GlassCard({
  children,
  className,
  variant = 'paper',
  ...rest
}: {
  children: ReactNode
  className?: string
  variant?: SurfaceVariant
} & HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(variant, 'rounded-[var(--radius-card)]', className)}
      {...rest}
    >
      {children}
    </div>
  )
}

/**
 * Compact glass pill — status labels, beta tags, trust items.
 * Always include a text label (no color-only meaning).
 */
export function GlassPill({
  children,
  dot,
  className,
}: {
  children: ReactNode
  /** Optional leading colored dot for liveness/status. */
  dot?: 'live' | 'neutral'
  className?: string
}) {
  const dotColor = dot === 'live' ? 'bg-emerald-500' : 'bg-[var(--color-ink-subtle)]'
  return (
    <span
      className={cn(
        'glass-subtle inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[12px] tracking-tight text-[var(--color-ink-muted)]',
        className,
      )}
    >
      {dot && (
        <span
          className={cn('inline-block w-1.5 h-1.5 rounded-full', dotColor)}
          aria-hidden
        />
      )}
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
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('glass-subtle rounded-[var(--radius-tile)]', className)}>
      {children}
    </div>
  )
}

export function MonoLabel({ children }: { children: ReactNode }) {
  return (
    <span className="font-mono text-[11px] tracking-[0.08em] uppercase text-[var(--color-ink-subtle)]">
      {children}
    </span>
  )
}
