# B7c — Score breakdown chart + risk list

**Goal:** Visualize the §5.7 fit-score breakdown (9 dimensions) and list risks (PRD §5.8) on the opportunity detail page.

**PRD references:** §5.7, §5.8, §5.10.
**Depends on:** B7a.
**Blocks:** none — last piece of B7.

---

## Files

```
/web/components/opportunities/FitScoreBreakdown.tsx
/web/components/opportunities/RiskList.tsx
/web/components/opportunities/RiskRow.tsx
```

Install if not already: `npm install recharts` (lightweight, fits Tailwind aesthetic).

---

## FitScoreBreakdown.tsx

Use horizontal bars with the dimension weights as max. Visual rule: filled portion = score, unfilled portion = remaining capacity.

```tsx
import type { FitScore } from "@/lib/schemas";

const DIMENSIONS = [
  { key: "capability", label: "Capability match", max: 20 },
  { key: "eligibility", label: "Eligibility", max: 15 },
  { key: "naics", label: "NAICS", max: 10 },
  { key: "past_performance", label: "Past performance", max: 15 },
  { key: "certification", label: "Certifications", max: 10 },
  { key: "insurance_bonding", label: "Insurance/bonding", max: 10 },
  { key: "deadline", label: "Deadline feasibility", max: 10 },
  { key: "complexity", label: "Proposal complexity", max: 5 },
  { key: "geography", label: "Geography", max: 5 },
] as const;

export function FitScoreBreakdown({ breakdown }: { breakdown: FitScore["score_breakdown"] }) {
  return (
    <div className="space-y-3">
      {DIMENSIONS.map(d => {
        const score = (breakdown as any)[d.key] ?? 0;
        const pct = (score / d.max) * 100;
        const tone = pct >= 75 ? "bg-decision-strong" : pct >= 50 ? "bg-decision-pursue" : pct >= 25 ? "bg-decision-maybe" : "bg-decision-reject";
        return (
          <div key={d.key} className="grid grid-cols-12 items-center gap-3 text-sm">
            <span className="col-span-4 text-ink">{d.label}</span>
            <div className="col-span-7 h-2 rounded-full bg-canvas-subtle overflow-hidden">
              <div className={`h-full ${tone} transition-all`} style={{ width: `${pct}%` }} />
            </div>
            <span className="col-span-1 text-right text-xs text-ink-muted tabular-nums">{score}/{d.max}</span>
          </div>
        );
      })}
    </div>
  );
}
```

---

## RiskList.tsx

Grouped by severity, criticals first.

```tsx
import { RiskRow } from "./RiskRow";
import type { RiskFlag } from "@/lib/schemas";

const SEVERITY_ORDER = ["critical_blocker", "major", "moderate", "minor"] as const;
const SEVERITY_LABELS: Record<string, string> = {
  critical_blocker: "Critical blockers",
  major: "Major risks",
  moderate: "Moderate concerns",
  minor: "Minor notes",
};

export function RiskList({ risks }: { risks: RiskFlag[] }) {
  if (risks.length === 0) {
    return <p className="text-sm text-ink-muted">No risks flagged.</p>;
  }

  const groups = SEVERITY_ORDER
    .map(sev => ({ severity: sev, items: risks.filter(r => r.severity === sev) }))
    .filter(g => g.items.length > 0);

  return (
    <div className="space-y-6">
      {groups.map(group => (
        <div key={group.severity}>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-muted mb-2">
            {SEVERITY_LABELS[group.severity]} ({group.items.length})
          </h3>
          <div className="space-y-2">
            {group.items.map((r, i) => <RiskRow key={i} risk={r} />)}
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## RiskRow.tsx

```tsx
import type { RiskFlag } from "@/lib/schemas";

const borderBySeverity: Record<string, string> = {
  critical_blocker: "border-severity-critical bg-severity-critical/5",
  major: "border-severity-major bg-severity-major/5",
  moderate: "border-severity-moderate",
  minor: "border-canvas-border",
};

export function RiskRow({ risk }: { risk: RiskFlag }) {
  return (
    <div className={`rounded-md border-l-4 ${borderBySeverity[risk.severity]} pl-4 py-3 pr-3`}>
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-semibold text-ink">{risk.title}</h4>
        {risk.requires_human_review && (
          <span className="text-xs text-decision-maybe">⚠ Needs review</span>
        )}
      </div>
      <p className="mt-1 text-sm text-ink leading-6">{risk.description}</p>
      {risk.evidence && (
        <p className="mt-2 text-xs italic text-ink-muted leading-5">
          Evidence: "{risk.evidence}"
        </p>
      )}
      <p className="mt-2 text-xs text-ink">
        <strong className="text-ink-muted">Mitigation:</strong> {risk.mitigation}
      </p>
    </div>
  );
}
```

---

## §11.1 visibility

For the **reject fixture**, the critical_blocker risk MUST be the visual focal point. The detail page already orders criticals first; ensure:

- Critical-blocker section heading reads "Critical blockers (1)" or however many.
- Background tint is visible without being garish.
- Evidence quote is shown verbatim (this is the source-cited proof).

This is the demo's §11.1 moment — practice clicking through to verify.

---

## Done when

- [ ] Strong-pursue: bars mostly green, no critical risks.
- [ ] Maybe: past-performance bar visibly low; major or moderate risk listed.
- [ ] Reject: critical_blocker risk prominent; eligibility bar at 0; evidence quote visible.
- [ ] Hover/tooltip on bars shows exact score (optional but nice).
- [ ] No external charting lib bloat — recharts is fine but if it adds > 100 KB, consider swapping for plain SVG bars (already done above with `div` widths).

## Verify

Open each fixture's detail page. Confirm visual differentiation:
- strong: mostly green bars
- maybe: mixed amber/green
- reject: red eligibility bar at 0, prominent critical-blocker card

## Pitfalls

- **Hardcoded breakdown keys.** Coordinate with A — the API's `score_breakdown` keys must match what's listed in `DIMENSIONS` above.
- **Reject visual underwhelms.** If criticals don't visually stand out, the §11.1 stage moment falls flat. Practice rehearsal-watching the audience.
- **Charting lib weight.** Recharts ships ~200 KB. The pure-Tailwind bars above are fine; skip the charting lib if you can.
