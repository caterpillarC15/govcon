# B8b — Compliance matrix component

**Goal:** PRD §5.11 — the compliance-matrix table. Each row: requirement, status, evidence, next action, owner.

**PRD references:** §5.11.
**Depends on:** B8a.
**Blocks:** B8c.

---

## Files

```
/web/components/packages/ComplianceMatrix.tsx
/web/components/packages/StatusPill.tsx
```

---

## ComplianceMatrix.tsx

```tsx
import { StatusPill } from "./StatusPill";
import type { ActionPackage } from "@/lib/schemas";

type Row = ActionPackage["compliance_matrix"][number];

export function ComplianceMatrix({ rows }: { rows: Row[] }) {
  if (rows.length === 0) {
    return null;
  }

  return (
    <section className="mt-12">
      <h2 className="text-xl font-semibold text-ink">Compliance matrix</h2>
      <p className="mt-2 text-sm text-ink-muted">
        How the company stacks up against each requirement, with the next action and owner.
      </p>

      <div className="mt-4 overflow-hidden rounded-md border border-canvas-border print:border-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-canvas-subtle text-left">
              <th className="px-4 py-2 font-medium text-ink">Requirement</th>
              <th className="px-4 py-2 font-medium text-ink w-32">Status</th>
              <th className="px-4 py-2 font-medium text-ink">Next action</th>
              <th className="px-4 py-2 font-medium text-ink w-32">Owner</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t border-canvas-border align-top">
                <td className="px-4 py-3">
                  <div className="text-ink">{row.requirement}</div>
                  {row.evidence && (
                    <p className="mt-1 text-xs italic text-ink-muted leading-5">"{row.evidence}"</p>
                  )}
                </td>
                <td className="px-4 py-3"><StatusPill status={row.status} /></td>
                <td className="px-4 py-3 text-ink">{row.next_action}</td>
                <td className="px-4 py-3 text-ink-muted text-xs">{row.owner ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

---

## StatusPill.tsx

```tsx
const styles: Record<string, string> = {
  met:            "bg-status-met/15 text-status-met",
  missing:        "bg-status-missing/15 text-status-missing",
  unclear:        "bg-status-unclear/15 text-status-unclear",
  not_applicable: "bg-status-na/15 text-status-na",
};

const labels: Record<string, string> = {
  met: "Met",
  missing: "Missing",
  unclear: "Unclear",
  not_applicable: "N/A",
};

export function StatusPill({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] ?? ""}`}>
      {labels[status] ?? status}
    </span>
  );
}
```

---

## Print behavior

The matrix is the most-printed section. Make it work clean:

- Borders thin and simple in print mode.
- No background colors (except the status pill, which prints as text + outline).

```css
@media print {
  table { page-break-inside: auto; }
  tr { page-break-inside: avoid; page-break-after: auto; }
}
```

---

## Done when

- [ ] Strong-pursue: ~6-10 rows, mostly "met"; some "unclear".
- [ ] Reject: 1-3 rows, includes "missing" for the blocker.
- [ ] Status pills color-coded AND text-labeled (don't rely on color alone — accessibility).
- [ ] Evidence quotes visible under each requirement.
- [ ] Print preview renders cleanly.

## Pitfalls

- **Status string drift.** API uses `not_applicable` (snake case); UI label is "N/A". Map with the dictionary above.
- **Long requirement text wraps poorly.** Cell `align-top` + leading-6 keeps it readable. Don't use `whitespace-nowrap`.
- **Empty matrix on reject packages.** Per A8, reject packages produce a slim matrix with the blocker rows. If `rows.length === 0`, return null (don't show an empty table).
