import { LegalShell } from '@/components/LegalShell'

export const metadata = { title: 'Terms of service' }

export default function TermsPage() {
  return (
    <LegalShell>
      <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-[var(--color-ink-muted)]">
        Terms
      </p>
      <h1 className="mt-2 text-[34px] font-semibold leading-[1.05] tracking-[-0.01em] text-[var(--color-ink)]">
        Terms of service
      </h1>
      <p>Last updated: May 2026.</p>

      <h2>The product</h2>
      <p>
        GovCon Bid Desk is a workspace for government-contracting teams to
        qualify opportunities, draft bid plans, and route action packages
        through human approval. The product is in private beta.
      </p>

      <h2>Acceptable use</h2>
      <p>
        Don&apos;t use the service to process classified material or CUI. Don&apos;t
        attempt to reverse-engineer, scrape, or rate-limit-bust the API. Per-key
        rate limits apply (60 req/min) and may change.
      </p>

      <h2>Approval gate</h2>
      <p>
        Action packages require explicit human approval before any external
        artifact is finalized. Nothing leaves your account autonomously.
      </p>

      <h2>Beta disclaimer</h2>
      <p>
        The service is provided &quot;as is&quot; during private beta. Bid/no-bid
        suggestions and fit scores are decision support, not legal or
        contractual advice.
      </p>

      <h2>Termination</h2>
      <p>
        Either party may terminate at any time. We retain audit trails for the
        period required by SAM.gov compliance, after which they are purged.
      </p>

      <h2>Contact</h2>
      <p>
        Questions: legal@govconbiddesk.com.
      </p>
    </LegalShell>
  )
}
