import { ArrowRight } from 'lucide-react'
import { GlassPill, LinkButton } from '../ui/Primitives'
import { HERO } from '../../data/copy'

export default function Hero() {
  return (
    <section className="relative w-full">
      <div className="mx-auto max-w-[1100px] px-5 sm:px-8 pt-10 sm:pt-14 pb-6 sm:pb-10 text-center">
        <GlassPill dot="live">{HERO.pill}</GlassPill>

        <h1
          className="mt-7 sm:mt-8 text-[44px] sm:text-[72px] lg:text-[104px] text-[var(--color-ink)] mx-auto"
          style={{
            lineHeight: 0.92,
            letterSpacing: 0,
            fontWeight: 600,
            maxWidth: '100%',
          }}
        >
          {HERO.title}
        </h1>

        <p
          className="mt-5 mx-auto max-w-2xl text-[var(--color-ink)]"
          style={{
            fontSize: 'clamp(18px, 2.4vw, 22px)',
            lineHeight: 1.4,
            letterSpacing: 0,
            fontWeight: 500,
          }}
        >
          A first-pass{' '}
          <span
            style={{
              fontFamily: 'var(--font-serif)',
              fontStyle: 'italic',
              fontWeight: 400,
              letterSpacing: '0',
            }}
            className="text-[var(--color-ink)]"
          >
            capture analyst
          </span>{' '}
          for federal contracts.
        </p>

        <p className="mt-3 mx-auto max-w-xl text-[14.5px] leading-[1.55] text-[var(--color-ink-muted)]">
          Extracts requirements with page-level citations, scores fit against
          your profile, and produces a reviewable action package. Human
          approval before anything external.
        </p>

        <div className="mt-7 flex flex-col sm:flex-row items-center justify-center gap-3">
          <LinkButton href="#waitlist" variant="primary" size="md">
            {HERO.primaryCta}
            <ArrowRight size={14} strokeWidth={2} />
          </LinkButton>
          <LinkButton href="#workflow" variant="secondary" size="md">
            {HERO.secondaryCta}
          </LinkButton>
        </div>
      </div>
    </section>
  )
}
