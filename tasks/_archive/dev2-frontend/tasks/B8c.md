# B8c — Risk register + proposal checklist + timeline + partner suggestions

**Goal:** PRD §5.11 — the middle sections of the action package. Risk register, proposal checklist, timeline, partner suggestions.

**PRD references:** §5.11, §5.12.
**Depends on:** B8a, B8b.
**Blocks:** B8d.

---

## Files

```
/web/components/packages/RiskRegister.tsx
/web/components/packages/ProposalChecklist.tsx
/web/components/packages/Timeline.tsx
/web/components/packages/PartnerSuggestions.tsx
```

---

## RiskRegister.tsx

Re-uses RiskRow visual from B7c but with the `risk_register` shape (slightly different schema):

```tsx
import type { ActionPackage } from "@/lib/schemas";

const borderBySeverity: Record<string, string> = {
  critical: "border-severity-critical bg-severity-critical/5",
  major: "border-severity-major bg-severity-major/5",
  moderate: "border-severity-moderate",
  minor: "border-canvas-border",
};

export function RiskRegister({ items }: { items: ActionPackage["risk_register"] }) {
  if (items.length === 0) {
    return (
      <section className="mt-12">
        <h2 className="text-xl font-semibold text-ink">Risk register</h2>
        <p className="mt-3 text-sm text-ink-muted">No outstanding risks.</p>
      </section>
    );
  }

  return (
    <section className="mt-12">
      <h2 className="text-xl font-semibold text-ink">Risk register</h2>
      <div className="mt-4 space-y-3">
        {items.map((r, i) => (
          <div key={i} className={`rounded-md border-l-4 ${borderBySeverity[r.severity]} pl-4 py-3 pr-3`}>
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink">{r.risk}</h3>
              <span className="text-xs uppercase text-ink-muted">{r.severity}</span>
            </div>
            <p className="mt-1 text-sm text-ink leading-6">{r.explanation}</p>
            <p className="mt-2 text-xs text-ink">
              <strong className="text-ink-muted">Mitigation:</strong> {r.mitigation}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
```

---

## ProposalChecklist.tsx

```tsx
import { Check } from "lucide-react";

export function ProposalChecklist({ items }: { items: string[] }) {
  if (items.length === 0) return null;

  return (
    <section className="mt-12">
      <h2 className="text-xl font-semibold text-ink">Proposal checklist</h2>
      <p className="mt-2 text-sm text-ink-muted">Concrete actions, ordered by priority.</p>
      <ul className="mt-4 space-y-2 text-sm">
        {items.map((item, i) => (
          <li key={i} className="flex gap-3">
            <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-decision-strong" />
            <span className="text-ink leading-6">{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

---

## Timeline.tsx (different from runs/Timeline.tsx)

```tsx
import type { ActionPackage } from "@/lib/schemas";

type Item = ActionPackage["timeline"][number];

export function Timeline({ items }: { items: Item[] }) {
  if (items.length === 0) return null;

  return (
    <section className="mt-12">
      <h2 className="text-xl font-semibold text-ink">Timeline to submission</h2>

      <ol className="mt-4 relative border-l-2 border-canvas-border pl-6 space-y-5">
        {items.map((item, i) => (
          <li key={i} className="relative">
            <span className="absolute -left-[33px] top-1 h-3 w-3 rounded-full border-2 border-canvas bg-accent" />
            <div className="text-xs uppercase tracking-wider text-ink-muted tabular-nums">{item.date}</div>
            <div className="text-sm text-ink mt-1">{item.task}</div>
            <div className="text-xs text-ink-muted mt-0.5">Owner: {item.owner ?? "—"}</div>
          </li>
        ))}
      </ol>
    </section>
  );
}
```

---

## PartnerSuggestions.tsx

```tsx
import type { ActionPackage } from "@/lib/schemas";

type Suggestion = NonNullable<ActionPackage["partner_suggestions"]>[number];

export function PartnerSuggestions({ items }: { items: Suggestion[] }) {
  if (items.length === 0) return null;

  return (
    <section className="mt-12">
      <h2 className="text-xl font-semibold text-ink">Partner / teaming suggestions</h2>
      <p className="mt-2 text-sm text-ink-muted">
        Capability or eligibility gaps a partner could close. Contact information is not provided — bring your own network.
      </p>

      <div className="mt-4 space-y-4">
        {items.map((s, i) => (
          <div key={i} className="rounded-md border border-canvas-border p-4">
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-sm font-semibold text-ink">{s.partner_type}</h3>
              <span className="text-xs uppercase text-ink-muted">Confidence: {s.confidence}</span>
            </div>
            <dl className="mt-3 space-y-2 text-sm">
              <div>
                <dt className="text-xs text-ink-muted">Gap solved</dt>
                <dd className="text-ink">{s.gap_solved}</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-muted">Why needed</dt>
                <dd className="text-ink">{s.why_needed}</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-muted">Suggested outreach angle</dt>
                <dd className="text-ink italic">"{s.outreach_angle}"</dd>
              </div>
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}
```

---

## Maybe-fixture demo moment

The maybe-needs-partner fixture (B10) drives this section — agent surfaces "team with a past-performance partner who has $8M+ in similar contracts." On stage, point it out: "concrete gap, concrete next step." Practice the click sequence.

---

## Done when

- [ ] Strong-pursue: risks, checklist, timeline rendered. No partner suggestions.
- [ ] Maybe: same + partner suggestion (past_performance_partner).
- [ ] Reject: only risk register; checklist, timeline, partners are all empty per A8 design.
- [ ] Print preview clean.

## Pitfalls

- **Empty section vs missing section.** When data is empty, return `null` so the page doesn't show empty headers. (Already handled above.)
- **Timeline dates as strings.** API returns ISO date strings. Don't parse or reformat unless necessary; let them render verbatim for predictability.
- **Partner suggestion overload.** A8 prompt caps at ~2 suggestions. If more come back, paginate or truncate gracefully.
