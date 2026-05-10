/**
 * Single source of truth for landing-page copy.
 *
 * Brand: SamRail — AI bid-desk operator for government-contracting
 * teams. Canonical source: tasks/LANDING_BRIEF.md.
 *
 * Public positioning rules (devdocs/V1_PRODUCT_ALIGNMENT.md §"Public Terms"):
 * sell the worker, not the framework; use bid / proposal / contract /
 * opportunity / action plan language; avoid leading with capture, MCP,
 * Hermes, OpenClaw, or "agent platform."
 */

export const PRODUCT = {
  name: 'SamRail',
  fullName: 'SamRail',
  tagline: 'AI bid-desk operator for government contracting teams.',
} as const

export const NAV = [
  { label: 'Workflow', href: '#workflow' },
  { label: 'Trust', href: '#trust' },
] as const

export const HERO = {
  pill: 'Private beta · onboarding design partners',
  title: 'Find contracts worth bidding before the deadline',
  subtitle:
    'Hire an AI operator that qualifies opportunities, drafts the bid plan, and keeps proposal work moving.',
  primaryCta: 'Start bid review',
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

export const TRUST_PILLS = [
  { label: 'Source-cited', sub: 'evidence + page #' },
  { label: 'Human-approved', sub: 'gate before external' },
  { label: 'Eligibility-conservative', sub: 'mismatch = reject' },
] as const

export const FOOTER = {
  // Footer.tsx renders the © + year separately; keep this string free of
  // both so we don't get a duplicate © on the rendered page.
  legal: 'SamRail · All rights reserved.',
} as const
