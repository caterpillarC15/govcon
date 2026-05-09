# B8a — Action package: executive brief + decision header

**Goal:** PRD §5.11 — the action-package page header section. Hero strip with decision, score, executive summary. Plus the **approval gate** at the top (§5.13) — non-removable, visible above the fold.

**PRD references:** §5.11, §5.13, §10.3.
**Depends on:** B2.
**Blocks:** B8b, B8c, B8d.

---

## Files

```
/web/app/action-packages/[id]/page.tsx
/web/components/packages/ApprovalGate.tsx
/web/components/packages/PackageHeader.tsx
/web/components/packages/ExecutiveBrief.tsx
```

---

## Page skeleton: app/action-packages/[id]/page.tsx

```tsx
'use client';

import { use } from "react";
import { useActionPackage } from "@/lib/hooks";
import { ApprovalGate } from "@/components/packages/ApprovalGate";
import { PackageHeader } from "@/components/packages/PackageHeader";
import { ExecutiveBrief } from "@/components/packages/ExecutiveBrief";
import { ComplianceMatrix } from "@/components/packages/ComplianceMatrix";   // B8b
import { RiskRegister } from "@/components/packages/RiskRegister";             // B8c
import { ProposalChecklist } from "@/components/packages/ProposalChecklist";   // B8c
import { Timeline } from "@/components/packages/Timeline";                     // B8c
import { PartnerSuggestions } from "@/components/packages/PartnerSuggestions"; // B8c
import { OutreachDraft } from "@/components/packages/OutreachDraft";           // B8d
import { ExportControls } from "@/components/packages/ExportControls";         // B8d
import { Skeleton } from "@/components/ui/skeleton";

export default function ActionPackagePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: pkg, isLoading } = useActionPackage(id);

  if (isLoading || !pkg) return <main className="p-12"><Skeleton className="h-96" /></main>;

  const isReject = pkg.decision === "reject";

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 print:py-0">
      <ApprovalGate items={pkg.human_approval_required} />
      <PackageHeader pkg={pkg} />
      <ExecutiveBrief summary={pkg.executive_summary} rationale={pkg.fit_rationale} />

      <ComplianceMatrix rows={pkg.compliance_matrix} />
      <RiskRegister items={pkg.risk_register} />

      {/* Reject decisions skip the prep-work sections */}
      {!isReject && <>
        <ProposalChecklist items={pkg.proposal_checklist} />
        <Timeline items={pkg.timeline} />
        <PartnerSuggestions items={pkg.partner_suggestions ?? []} />
        <OutreachDraft draft={pkg.outreach_draft} />
      </>}

      <ExportControls pkg={pkg} />
    </main>
  );
}
```

---

## ApprovalGate.tsx (PRD §5.13)

Sticky at top, attention-grabbing without being shrill. **Always present, even on reject packages.**

```tsx
import { AlertTriangle } from "lucide-react";

export function ApprovalGate({ items }: { items: string[] }) {
  return (
    <div className="rounded-lg border-2 border-decision-reject/40 bg-decision-reject/5 p-5 mb-8 print:border print:bg-white">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 flex-shrink-0 text-decision-reject" />
        <div className="flex-1">
          <h2 className="text-base font-semibold text-decision-reject">Human approval required</h2>
          <p className="mt-2 text-sm text-ink leading-6">
            Do not send emails, submit materials, claim certifications, or mark compliance complete without authorized review.
          </p>
          {items?.length > 0 && (
            <ul className="mt-3 space-y-1 text-sm text-ink">
              {items.map((item, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-ink-muted">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## PackageHeader.tsx

Decision + score + opportunity reference + agency/solicitation number:

```tsx
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import type { ActionPackage } from "@/lib/schemas";

export function PackageHeader({ pkg }: { pkg: ActionPackage }) {
  return (
    <header className="mb-10 border-b border-canvas-border pb-8">
      <p className="text-xs uppercase tracking-wider text-ink-muted">
        Action package · prepared {new Date().toLocaleDateString()}
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink font-serif">
        {pkg.opportunity_title ?? "Opportunity"}
      </h1>
      <div className="mt-4 flex items-center gap-3">
        <DecisionBadge decision={pkg.decision as any} score={pkg.fit_score} />
        <span className="text-sm text-ink-muted">·</span>
        <span className="text-sm text-ink">{pkg.opportunity_agency ?? ""}</span>
        {pkg.opportunity_solicitation_number && (
          <>
            <span className="text-sm text-ink-muted">·</span>
            <code className="text-xs font-mono text-ink-muted">{pkg.opportunity_solicitation_number}</code>
          </>
        )}
      </div>
    </header>
  );
}
```

---

## ExecutiveBrief.tsx

```tsx
export function ExecutiveBrief({ summary, rationale }: { summary: string; rationale: string }) {
  return (
    <section className="mt-8 space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-ink">Executive summary</h2>
        <p className="mt-3 text-base text-ink leading-7 font-serif">{summary}</p>
      </div>
      <div>
        <h3 className="text-base font-semibold text-ink">Rationale</h3>
        <p className="mt-2 text-base text-ink leading-7 font-serif">{rationale}</p>
      </div>
    </section>
  );
}
```

Use `font-serif` (Source Serif 4 from DESIGN.md) for the document feel.

---

## Print styles

The approval gate prints with a simpler border (no fill); navigation/buttons hidden via `print:hidden`. Print-only disclaimer:

```tsx
<div className="hidden print:block text-xs text-ink-muted mb-4 italic">
  Generated by GovCapture Agent. Human approval required before any external action.
</div>
```

---

## Done when

- [ ] All three demo fixtures' action packages render the header + executive brief + approval gate.
- [ ] Reject fixture: decision badge red; rationale references the blocker; approval gate present.
- [ ] Print preview renders document-grade (serif body, no chrome).
- [ ] Approval gate is unmissable — first thing scrolled to.

## Pitfalls

- **Approval gate fading visually under load.** The reject color tint is on purpose — it draws the eye. Don't soften.
- **Header relying on opportunity fields the API doesn't return.** Confirm with A which fields are denormalized into `ActionPackage` vs requiring a separate fetch. If separate, fetch in parallel.
- **Print stylesheet broken.** Run `Cmd+P` regularly during dev. Tailwind's `print:` variants help but you'll find edge cases.
