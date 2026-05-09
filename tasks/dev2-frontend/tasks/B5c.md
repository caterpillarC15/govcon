# B5c — Step row + tool-call detail expander

**Goal:** Each timeline row shows step label + status; expanding shows the tool calls inside (rationale, input, output, latency, cost). **This is the "verifiable agent" UX.**

**PRD references:** §5.3, §4.5 observability.
**Depends on:** B5a, B5b.
**Blocks:** B7 (evidence-snippet links go through here).

---

## Files

```
/web/components/runs/StepRow.tsx
/web/components/runs/ToolCallDetail.tsx
/web/components/runs/StatusBadge.tsx
/web/components/ui/JsonViewer.tsx              # small pretty-print component
```

---

## StepRow.tsx

```tsx
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { ToolCallDetail } from "./ToolCallDetail";
import { StatusBadge } from "./StatusBadge";
import type { StepState } from "@/lib/hooks/useAgentRunStream";

export function StepRow({ step, index }: { step: StepState; index: number }) {
  const [open, setOpen] = useState(false);

  return (
    <li className="rounded-md border border-canvas-border bg-canvas">
      <button
        className="flex w-full items-center gap-3 p-3 text-left hover:bg-canvas-subtle transition-colors"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <span className="text-xs text-ink-muted tabular-nums">{String(index).padStart(2, "0")}</span>
        {open ? <ChevronDown className="h-4 w-4 text-ink-muted" /> : <ChevronRight className="h-4 w-4 text-ink-muted" />}
        <span className="flex-1 text-sm text-ink">{step.label}</span>
        <StatusBadge status={step.status} />
        {step.toolCalls.length > 0 && (
          <span className="text-xs text-ink-muted tabular-nums">
            {step.toolCalls.length} {step.toolCalls.length === 1 ? "call" : "calls"}
          </span>
        )}
      </button>

      {open && (
        <div className="border-t border-canvas-border bg-canvas-subtle px-4 py-3 space-y-3">
          {step.toolCalls.length === 0 ? (
            <p className="text-xs text-ink-muted">No tool calls yet.</p>
          ) : (
            step.toolCalls.map((c, i) => <ToolCallDetail key={i} call={c} />)
          )}
        </div>
      )}
    </li>
  );
}
```

---

## ToolCallDetail.tsx

```tsx
import { JsonViewer } from "@/components/ui/JsonViewer";

export function ToolCallDetail({ call }: { call: any }) {
  return (
    <div className="rounded border border-canvas-border bg-canvas p-3 text-sm space-y-2">
      <div className="flex items-center justify-between gap-2">
        <code className="rounded bg-accent-subtle px-2 py-0.5 text-xs font-mono text-accent">
          {call.tool}
        </code>
        <div className="flex items-center gap-3 text-xs text-ink-muted tabular-nums">
          {call.latency_ms !== undefined && <span>{call.latency_ms} ms</span>}
          {call.cost_usd !== undefined && <span>${call.cost_usd.toFixed(4)}</span>}
        </div>
      </div>

      {call.rationale && (
        <p className="text-xs italic text-ink-muted leading-5">"{call.rationale}"</p>
      )}

      <details className="text-xs">
        <summary className="cursor-pointer text-ink-muted hover:text-ink">Input</summary>
        <JsonViewer value={call.input} className="mt-2" />
      </details>

      {call.error ? (
        <div className="rounded border border-decision-reject/30 bg-decision-reject/5 p-2 text-xs text-decision-reject">
          <strong>Error:</strong> {call.error}
        </div>
      ) : call.output !== undefined ? (
        <details className="text-xs">
          <summary className="cursor-pointer text-ink-muted hover:text-ink">Output</summary>
          <JsonViewer value={call.output} className="mt-2" />
        </details>
      ) : (
        <p className="text-xs text-ink-muted">Pending…</p>
      )}
    </div>
  );
}
```

---

## StatusBadge.tsx

```tsx
const styles: Record<string, string> = {
  running:      "bg-accent-subtle text-accent",
  complete:     "bg-decision-strong/15 text-decision-strong",
  degraded:     "bg-decision-maybe/15 text-decision-maybe",
  failed:       "bg-decision-reject/15 text-decision-reject",
  needs_review: "bg-severity-major/15 text-severity-major",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wider ${styles[status] ?? ""}`}>
      {status}
    </span>
  );
}
```

---

## JsonViewer.tsx

Plain `<pre>` is fine for v1; add a copy-button:

```tsx
import { useState } from "react";

export function JsonViewer({ value, className = "" }: { value: unknown; className?: string }) {
  const [copied, setCopied] = useState(false);
  const json = typeof value === "string" ? value : JSON.stringify(value, null, 2);

  return (
    <div className={`relative ${className}`}>
      <pre className="overflow-x-auto rounded bg-canvas p-3 text-xs font-mono text-ink-muted leading-5 max-h-64">
        {json}
      </pre>
      <button
        className="absolute right-2 top-2 rounded border border-canvas-border bg-canvas px-2 py-0.5 text-xs hover:border-accent"
        onClick={() => {
          navigator.clipboard.writeText(json);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
      >
        {copied ? "✓" : "Copy"}
      </button>
    </div>
  );
}
```

---

## Done when

- [ ] Click a step row → expander opens; shows all tool calls within.
- [ ] Rationale visible per tool call.
- [ ] Input/output viewable as JSON, copyable.
- [ ] Latency and cost rendered when present.
- [ ] Error state visually distinct (red border + message).
- [ ] Keyboard navigation works (Enter/Space to toggle expander).
- [ ] On the demo, clicking `extract_requirements` for the strong-pursue opportunity reveals the full extracted-requirements JSON — judges can see the agent's actual output.

## Verify

Open a step in the timeline; expand; confirm tool calls render with rationale, latency, cost, input, output. Click Copy on input — paste into a notes app, confirm valid JSON.

## Pitfalls

- **Massive JSON outputs (extracted requirements with snippets) overflow.** Cap height with `max-h-64 overflow-x-auto`; user scrolls.
- **`<details>` inside `<button>` doesn't work.** Don't nest interactive elements. The expander button is on the row; the details are inside the open panel.
- **Scrollbars looking ugly on Windows.** Tailwind's scrollbar styling helps; `scrollbar-thin scrollbar-thumb-canvas-border` plugins.
- **Re-renders on every event.** Memoize `ToolCallDetail` so unrelated step updates don't re-render every detail panel.
