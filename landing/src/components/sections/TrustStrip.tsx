import { GlassCard } from '../ui/Primitives'
import { TRUST_PILLS } from '../../data/copy'
import { cn } from '../../lib/cn'

/**
 * Compact trust strip — four commitments in one glass row.
 * Promoted to `glass-strong` so it carries the same material weight
 * as the workflow cards above. Dividers are tuned for translucency:
 * a faint slate line + 1px white shine, so they read on glass without
 * going opaque.
 */
export default function TrustStrip() {
  const divider =
    'border-[rgba(15,23,42,0.07)] shadow-[inset_0_-1px_0_rgba(255,255,255,0.6)]'

  return (
    <section id="trust" className="relative w-full" aria-labelledby="trust-heading">
      <div className="mx-auto max-w-[1100px] px-5 sm:px-8 pb-12 sm:pb-16">
        <h2 id="trust-heading" className="sr-only">
          What stays in your control
        </h2>
        <GlassCard variant="glass-strong" className="p-2">
          <ul className="grid grid-cols-2 md:grid-cols-4">
            {TRUST_PILLS.map((p, i) => (
              <li
                key={p.label}
                className={cn(
                  'px-5 py-6 flex flex-col items-start',
                  // mobile (2 cols): right + bottom hairlines, no edges
                  i % 2 === 0 && `border-r ${divider}`,
                  i < 2 && `border-b ${divider}`,
                  // desktop (4 cols): only between columns
                  'md:border-b-0',
                  i !== 0 ? `md:border-l ${divider}` : 'md:border-l-0',
                  i % 2 !== 0 && 'md:border-r-0',
                )}
              >
                <span className="text-[13.5px] font-semibold tracking-[-0.012em] text-[var(--color-ink)]">
                  {p.label}
                </span>
                <span className="mt-1.5 text-[11.5px] text-[var(--color-ink-muted)] font-mono tracking-tight">
                  {p.sub}
                </span>
              </li>
            ))}
          </ul>
        </GlassCard>
      </div>
    </section>
  )
}
