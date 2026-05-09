/**
 * Single source of truth for landing-page copy.
 * Defensible against PRD §15 (Outreach Positioning):
 * — say "first-pass capture analysis," "human-reviewed workflow"
 * — never claim "guaranteed eligibility," "automatic submission," "legal review"
 */

export const PRODUCT = {
  name: 'GovCapture',
  fullName: 'GovCapture Agent',
} as const

export const NAV = [
  { label: 'Workflow', href: '#workflow' },
  { label: 'Trust', href: '#trust' },
] as const

export const HERO = {
  pill: 'Private beta · onboarding design partners',
  title: 'GovCapture',
  subtitle: 'A first-pass capture analyst for federal contracts.',
  primaryCta: 'Request access',
  secondaryCta: 'See the workflow',
} as const

export const STORY_CARDS = [
  {
    n: '01',
    label: 'DISCOVER',
    title: 'Match opportunities',
    body: 'SAM.gov by capability, NAICS, set-aside. Cached and seeded fallbacks if live calls fail.',
  },
  {
    n: '02',
    label: 'EXTRACT',
    title: 'Read with citations',
    body: 'Page-level PDF parsing. Every line carries confidence, evidence, and a clickable page number.',
  },
  {
    n: '03',
    label: 'DECIDE',
    title: 'Pursue, maybe, or reject',
    body: '100-point rubric across 9 dimensions. Eligibility mismatch is always a critical blocker.',
  },
] as const

export const METRICS = [
  { value: '40', caption: 'Steps per run' },
  { value: '6 min', caption: 'Wall-clock ceiling' },
  { value: '$0.50', caption: 'LLM-cost ceiling' },
] as const

export const TRUST_PILLS = [
  { label: 'Source-cited', sub: 'evidence + page #' },
  { label: 'Human-approved', sub: 'gate before external' },
  { label: 'Eligibility-conservative', sub: 'mismatch = reject' },
  { label: 'Bounded runs', sub: '40 steps · 6 min · $0.50' },
] as const

export const FOOTER = {
  blurb: 'MVP for the Agents Track',
  legal: '© ' + new Date().getFullYear() + ' GovCapture. Source-cited; not legal advice.',
} as const
