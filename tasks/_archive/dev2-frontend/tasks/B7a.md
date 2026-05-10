# B7a — Opportunity detail layout + sections

**Goal:** PRD §5.10 detail-view layout. Sections for summary, requirements, evidence, fit-score breakdown, risks, missing info, recommended next action, source documents.

**PRD references:** §5.10.
**Depends on:** B2.
**Blocks:** B7b, B7c.

---

## Files

```
/web/app/opportunities/[id]/page.tsx
/web/components/opportunities/OpportunityDetail.tsx       # the page-level component
/web/components/opportunities/RequirementList.tsx
/web/components/opportunities/RequirementRow.tsx
```

---

## Layout

Single-column, document-feel. ~720px max width. Sections separated by `<hr>` with generous spacing.

```tsx
'use client';

import { use } from "react";
import { useOpportunity, useRequirements, useFitScore, useRisks } from "@/lib/hooks";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { RequirementList } from "@/components/opportunities/RequirementList";
import { FitScoreBreakdown } from "@/components/opportunities/FitScoreBreakdown";   // B7c
import { RiskList } from "@/components/opportunities/RiskList";                       // B7c
import { Skeleton } from "@/components/ui/skeleton";

export default function OpportunityPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: opp } = useOpportunity(id);
  const { data: reqs } = useRequirements(id);
  const { data: fitScore } = useFitScore(id);
  const { data: risks } = useRisks(id);

  if (!opp) return <main className="p-12">Loading…</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-ink-muted">{opp.agency}</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-ink">{opp.title}</h1>
          <p className="mt-2 text-sm text-ink-muted">{opp.solicitation_number}</p>
        </div>
        {fitScore && <DecisionBadge decision={fitScore.decision} score={fitScore.total_score} />}
      </div>

      {/* Quick facts */}
      <dl className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 rounded-md border border-canvas-border bg-canvas-subtle p-4 text-xs">
        <Fact label="NAICS" value={opp.naics} />
        <Fact label="Set-aside" value={opp.set_aside} />
        <Fact label="Due" value={opp.due_date} />
        <Fact label="Place" value={opp.place_of_performance} />
      </dl>

      <Section title="Summary">
        <p className="text-sm text-ink leading-7">{opp.description}</p>
      </Section>

      <Section title="Recommended next action">
        <p className="text-sm text-ink leading-7">{fitScore?.recommended_next_action ?? "—"}</p>
      </Section>

      <Section title="Fit score breakdown" subtitle={`${fitScore?.total_score ?? "?"}/100`}>
        {fitScore && <FitScoreBreakdown breakdown={fitScore.score_breakdown} />}
      </Section>

      <Section title="Strengths and weaknesses">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
          <div>
            <h3 className="text-xs uppercase tracking-wider text-decision-strong mb-2">Strengths</h3>
            <ul className="space-y-1">{(fitScore?.strengths ?? []).map((s, i) => <li key={i}>• {s}</li>)}</ul>
          </div>
          <div>
            <h3 className="text-xs uppercase tracking-wider text-severity-major mb-2">Weaknesses</h3>
            <ul className="space-y-1">{(fitScore?.weaknesses ?? []).map((s, i) => <li key={i}>• {s}</li>)}</ul>
          </div>
        </div>
      </Section>

      <Section title="Risks">
        <RiskList risks={risks ?? []} />
      </Section>

      <Section title="Extracted requirements" subtitle={`${reqs?.length ?? 0} found`}>
        <RequirementList requirements={reqs ?? []} opportunityId={id} />
      </Section>

      <Section title="Missing information">
        {(fitScore?.missing_information?.length ?? 0) === 0 ? (
          <p className="text-sm text-ink-muted">None — all expected fields extracted with confidence.</p>
        ) : (
          <ul className="text-sm text-ink space-y-1">
            {fitScore!.missing_information.map((m, i) => <li key={i}>• {m}</li>)}
          </ul>
        )}
      </Section>

      <Section title="Source documents">
        <ul className="text-sm space-y-1">
          {(opp.attachments ?? []).map((a, i) => (
            <li key={i}>
              <a href={a.url} className="text-accent hover:underline" target="_blank" rel="noopener">
                {a.name ?? a.url}
              </a>
            </li>
          ))}
        </ul>
      </Section>

      <div className="mt-12">
        <a href={`/action-packages/${opp.id}`} className="inline-flex rounded-md bg-accent px-4 py-2 text-sm font-medium text-canvas hover:bg-accent-hover">
          View action package →
        </a>
      </div>
    </main>
  );
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="mt-10">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-semibold text-ink">{title}</h2>
        {subtitle && <span className="text-xs text-ink-muted tabular-nums">{subtitle}</span>}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Fact({ label, value }: { label: string; value: string | undefined | null }) {
  return (
    <div>
      <dt className="text-ink-muted">{label}</dt>
      <dd className="mt-0.5 text-ink truncate">{value ?? "—"}</dd>
    </div>
  );
}
```

---

## RequirementList.tsx

Groups requirements by type. Each row is a `RequirementRow` (B7b adds the click-to-PDF behavior).

```tsx
import { RequirementRow } from "./RequirementRow";

const TYPE_ORDER = [
  "eligibility", "security", "certification", "technical",
  "past_performance", "submission", "evaluation", "deadline",
  "location", "pricing", "insurance", "bonding", "document_required",
];

const TYPE_LABELS: Record<string, string> = {
  eligibility: "Eligibility",
  security: "Security / Clearance",
  certification: "Certifications",
  technical: "Technical scope",
  past_performance: "Past performance",
  submission: "Submission",
  evaluation: "Evaluation criteria",
  deadline: "Deadlines",
  location: "Location",
  pricing: "Pricing",
  insurance: "Insurance",
  bonding: "Bonding",
  document_required: "Required documents",
};

export function RequirementList({ requirements, opportunityId }: { requirements: ExtractedRequirement[]; opportunityId: string }) {
  if (requirements.length === 0) return <p className="text-sm text-ink-muted">No requirements extracted.</p>;

  const groups = TYPE_ORDER
    .map(type => ({ type, items: requirements.filter(r => r.type === type) }))
    .filter(g => g.items.length > 0);

  return (
    <div className="space-y-6">
      {groups.map(group => (
        <div key={group.type}>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-muted mb-2">
            {TYPE_LABELS[group.type] ?? group.type} ({group.items.length})
          </h3>
          <ul className="space-y-2">
            {group.items.map((req, i) => (
              <RequirementRow key={i} requirement={req} opportunityId={opportunityId} />
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
```

---

## RequirementRow.tsx (skeleton; B7b extends)

```tsx
import type { ExtractedRequirement } from "@/lib/schemas";

export function RequirementRow({ requirement, opportunityId }: { requirement: ExtractedRequirement; opportunityId: string }) {
  const blockerStyle = requirement.is_blocker ? "border-decision-reject" : "border-canvas-border";

  return (
    <li className={`rounded-md border-l-4 ${blockerStyle} bg-canvas py-2 pl-4 pr-3`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm text-ink"><strong>{requirement.title}:</strong> {requirement.value}</p>
          {requirement.description && (
            <p className="mt-0.5 text-xs text-ink-muted leading-5">{requirement.description}</p>
          )}
        </div>
        <ConfidenceBadge confidence={requirement.confidence} />
      </div>
      {/* Evidence button — B7b adds the deep-link behavior */}
      {requirement.evidence_snippet && requirement.page_number && (
        <EvidenceLink
          opportunityId={opportunityId}
          docId={requirement.source_document}
          page={requirement.page_number}
          snippet={requirement.evidence_snippet}
        />
      )}
    </li>
  );
}
```

---

## Done when

- [ ] Strong-pursue, maybe, reject all render the detail page correctly.
- [ ] Reject: clearance critical_blocker requirement is visually flagged (red border).
- [ ] All sections present; empty states for missing data.
- [ ] Action-package link works.

## Pitfalls

- **Long requirement lists.** > 25 requirements gets unwieldy. Group by type (already done above) and consider collapsible groups.
- **`requirement.is_blocker` flag.** Critical for the demo — the reject card must visibly show the blocker. Don't bury it.
- **Section spacing inconsistency.** Use the `Section` wrapper component throughout.
