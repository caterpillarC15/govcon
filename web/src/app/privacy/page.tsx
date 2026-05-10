import { LegalShell } from '@/components/LegalShell'

export const metadata = { title: 'Privacy policy' }

export default function PrivacyPage() {
  return (
    <LegalShell>
      <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-[var(--color-ink-muted)]">
        Privacy
      </p>
      <h1 className="mt-2 text-[34px] font-semibold leading-[1.05] tracking-[-0.01em] text-[var(--color-ink)]">
        Privacy policy
      </h1>
      <p>Last updated: May 2026.</p>

      <h2>What we collect</h2>
      <p>
        We collect the email you use to sign in, the company-profile data you
        enter (capabilities, NAICS codes, certifications, location, clearance
        status), and the goals and opportunities you generate during a run.
      </p>

      <h2>What we don&apos;t collect</h2>
      <p>
        We don&apos;t collect classified material, controlled unclassified
        information (CUI), or proposal text on your behalf — you remain the
        author of every external artifact.
      </p>

      <h2>How we use it</h2>
      <p>
        Your data powers the bid-desk workspace, drives matching against
        SAM.gov solicitations, and produces audit trails on each run. We do not
        sell or share data with third parties for marketing.
      </p>

      <h2>Subprocessors</h2>
      <p>
        Supabase (auth + Postgres), Anthropic (LLM inference), Resend (email),
        and SAM.gov (public solicitation data). Each is bound by data-processing
        agreements that prohibit secondary use.
      </p>

      <h2>Retention &amp; deletion</h2>
      <p>
        You can delete your account at any time from the API keys page. We
        purge profile data and run history within 30 days of account deletion.
      </p>

      <h2>Contact</h2>
      <p>
        Questions: privacy@samrail.com. We answer within 5 business days.
      </p>
    </LegalShell>
  )
}
