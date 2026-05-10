import { Badge, GlassCard, InnerTile, MonoLabel } from '../ui/Primitives'
import { STORY_CARDS } from '../../data/copy'
import FitScoreGauge from '../FitScoreGauge'

/* ------- Per-card supporting UI previews -------
 * One strong proof element per card. The glass surface is the hero;
 * the preview is a quiet anchor that earns the claim above it.
 *
 * Each preview is illustrative — labelled "Example output" so visitors
 * don't read the screenshot data as live or as a customer commitment.
 */

function DiscoverPreview() {
  return (
    <div className="flex flex-col gap-2.5">
      <MonoLabel>Example output</MonoLabel>
      <InnerTile className="px-3.5 py-3 flex items-center gap-3">
        <span className="font-mono text-[10px] tracking-[0.12em] text-[var(--color-ink-subtle)] shrink-0">
          DLA
        </span>
        <span className="text-[12.5px] text-[var(--color-ink)] truncate flex-1 min-w-0">
          Cyber Vuln Assessment
        </span>
        <Badge tone="strong_pursue" mono>
          88
        </Badge>
      </InnerTile>
      <p className="font-mono text-[10.5px] text-[var(--color-ink-subtle)] tracking-tight pl-1">
        + 13 ranked below · cached fallback when SAM is rate-limited
      </p>
    </div>
  )
}

function ExtractPreview() {
  return (
    <InnerTile className="p-4">
      <div className="flex items-center justify-between mb-2.5">
        <span className="font-mono text-[10px] tracking-[0.16em] uppercase text-[var(--color-ink)]">
          Eligibility
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500"
            aria-hidden
          />
          <span className="font-mono text-[10px] text-[var(--color-ink-subtle)]">
            high · p.3
          </span>
        </span>
      </div>
      <p
        className="text-[13px] leading-[1.55] text-[var(--color-ink)]"
        style={{ fontFamily: 'var(--font-serif)', fontStyle: 'italic' }}
      >
        “…set aside 100% for small business concerns under NAICS 541512…”
      </p>
    </InnerTile>
  )
}

function DecidePreview() {
  return (
    /* Layout adapts to per-card width:
     *   < 360  (very narrow phones)        — stack vertical
     *   360–767 (typical phone single-col) — horizontal, fits comfortably
     *   md 768–1023 (tight 3-col grid)     — stack vertical
     *   lg+ 1024+   (wide 3-col grid)      — horizontal
     */
    <InnerTile className="p-4 flex flex-col gap-3 min-[360px]:flex-row min-[360px]:items-center min-[360px]:gap-4 md:flex-col md:items-stretch md:gap-3 lg:flex-row lg:items-center lg:gap-4">
      <div className="-my-1 shrink-0">
        <FitScoreGauge score={88} decision="strong_pursue" size={104} />
      </div>
      <div className="flex-1 min-w-0">
        <Badge tone="strong_pursue">Strong pursue</Badge>
        <p className="mt-2.5 text-[11.5px] leading-[1.5] text-[var(--color-ink-muted)]">
          <span className="font-mono text-[var(--color-decision-reject)] tracking-[0.06em]">
            1 blocker
          </span>{' '}
          · past-performance refs need federal format.
        </p>
      </div>
    </InnerTile>
  )
}

const PREVIEWS = [DiscoverPreview, ExtractPreview, DecidePreview] as const

export default function StoryCards() {
  return (
    <section
      id="workflow"
      className="relative w-full"
      aria-labelledby="workflow-heading"
    >
      <div className="mx-auto max-w-[1200px] px-5 sm:px-8 pt-2 sm:pt-4 pb-14 sm:pb-20">
        <h2 id="workflow-heading" className="sr-only">
          How it works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 md:items-stretch gap-5 sm:gap-6">
          {STORY_CARDS.map((card, i) => {
            const Preview = PREVIEWS[i]
            if (!Preview) return null
            return (
              <GlassCard
                key={card.n}
                variant="glass-strong"
                className="card-rise p-7 sm:p-8 flex flex-col gap-6 glass-interactive h-full"
                /* Stagger entrance — pure CSS keyframe defined in
                   globals.css. SSR-safe; respects reduced motion. */
                style={{ animationDelay: `${i * 90}ms` }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[12px] tracking-[0.08em] text-[var(--color-ink-subtle)]">
                    [{card.n}]
                  </span>
                  <span className="font-mono text-[10.5px] tracking-[0.18em] text-[var(--color-ink)]">
                    {card.label}
                  </span>
                </div>

                <h3
                  className="text-[var(--color-ink)]"
                  style={{
                    fontSize: 'clamp(22px, 2.5vw, 28px)',
                    lineHeight: 1.1,
                    letterSpacing: '-0.022em',
                    fontWeight: 600,
                  }}
                >
                  {card.title}
                </h3>

                <p className="text-[13.5px] leading-[1.6] text-[var(--color-ink-muted)]">
                  {card.body}
                </p>

                <div className="mt-auto pt-2">
                  <Preview />
                </div>
              </GlassCard>
            )
          })}
        </div>
      </div>
    </section>
  )
}
