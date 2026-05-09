import { Badge, GlassCard, InnerTile } from '../ui/Primitives'
import { STORY_CARDS } from '../../data/copy'
import FitScoreGauge from '../FitScoreGauge'

/* ------- Per-card supporting UI previews ------- */

function DiscoverPreview() {
  const opps = [
    { agency: 'DLA', title: 'Cyber Vuln Assessment', tags: ['SB', '541512'], score: 88, tone: 'strong_pursue' as const },
    { agency: 'VA', title: 'Cloud Migration Support', tags: ['SDVOSB', '541519'], score: 64, tone: 'maybe' as const },
    { agency: 'DCSA', title: 'SCIF Network Ops', tags: ['8(a)', '541512'], score: 32, tone: 'reject' as const },
  ]
  return (
    <InnerTile className="p-2.5">
      <div className="px-2 pb-2 flex items-center justify-between border-b border-[var(--color-paper-line)]">
        <span className="font-mono text-[10px] text-[var(--color-ink-subtle)] tracking-tight">
          goal: cybersec · 60d
        </span>
        <span className="font-mono text-[10px] text-[var(--color-ink-subtle)]">
          14 hits
        </span>
      </div>
      <ul className="flex flex-col">
        {opps.map((o) => (
          <li
            key={o.agency}
            className="flex items-center gap-2 px-2 py-2 border-b border-[var(--color-paper-line)] last:border-b-0"
          >
            <span className="font-mono text-[9.5px] text-[var(--color-ink-subtle)] w-9 shrink-0">
              {o.agency}
            </span>
            <span className="text-[11.5px] text-[var(--color-ink)] truncate flex-1 min-w-0">
              {o.title}
            </span>
            <span className="hidden sm:flex items-center gap-1 shrink-0">
              {o.tags.map((t) => (
                <span
                  key={t}
                  className="font-mono text-[9.5px] text-[var(--color-ink-muted)] bg-white/60 border border-[var(--color-paper-line)] rounded px-1.5 py-0.5"
                >
                  {t}
                </span>
              ))}
            </span>
            <Badge tone={o.tone} mono>
              {o.score}
            </Badge>
          </li>
        ))}
      </ul>
    </InnerTile>
  )
}

function ExtractPreview() {
  const reqs = [
    {
      type: 'eligibility',
      page: 3,
      snippet: '“…set aside 100% for small business concerns under NAICS 541512…”',
    },
    {
      type: 'deadline',
      page: 4,
      snippet: '“Offers due Fri 19 Sep 2026 at 16:00 ET, per Block 8 of SF 33.”',
    },
  ]
  return (
    <div className="flex flex-col gap-2">
      {reqs.map((r) => (
        <InnerTile key={r.type} className="p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-[10px] text-[var(--color-ink-muted)] uppercase tracking-[0.1em]">
              {r.type}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" aria-hidden />
              <span className="font-mono text-[10px] text-[var(--color-ink-subtle)]">
                high · p.{r.page}
              </span>
            </span>
          </div>
          <p className="text-[11.5px] leading-snug text-[var(--color-ink)] font-mono">
            {r.snippet}
          </p>
        </InnerTile>
      ))}
    </div>
  )
}

function DecidePreview() {
  return (
    <InnerTile className="p-3">
      <div className="flex items-center gap-3">
        <div className="-my-1 shrink-0">
          <FitScoreGauge score={88} decision="strong_pursue" size={120} />
        </div>
        <div className="flex-1 min-w-0">
          <Badge tone="strong_pursue">Strong pursue</Badge>
          <div className="mt-2">
            <span className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-[var(--color-ink-subtle)]">
              Compliance
            </span>
            <div className="mt-1 flex flex-wrap items-center gap-1">
              <Badge tone="met" mono>
                MET
              </Badge>
              <Badge tone="met" mono>
                MET
              </Badge>
              <Badge tone="unclear" mono>
                UNCLEAR
              </Badge>
              <Badge tone="missing" mono>
                MISSING
              </Badge>
            </div>
          </div>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-[var(--color-paper-line)]">
        <span className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-[var(--color-decision-reject)]">
          Blocker · 1
        </span>
        <p className="mt-1 text-[11px] leading-snug text-[var(--color-ink-muted)]">
          Past-performance write-up needs federal references reformatted.
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
            return (
              <GlassCard
                key={card.n}
                variant="glass-strong"
                className="p-6 sm:p-7 flex flex-col gap-5 glass-interactive"
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
                    fontSize: 'clamp(20px, 2.4vw, 26px)',
                    lineHeight: 1.1,
                    letterSpacing: '-0.02em',
                    fontWeight: 600,
                  }}
                >
                  {card.title}
                </h3>

                <p className="text-[13.5px] leading-[1.6] text-[var(--color-ink-muted)]">
                  {card.body}
                </p>

                <div className="mt-auto pt-4">
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
