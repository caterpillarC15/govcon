# B5b — Timeline component (page-level)

**Goal:** PRD §5.3 — the visible run-progress timeline. Page that hosts the SSE consumer (B5a) and renders one row per step. **The wow moment of the demo.**

**PRD references:** §5.3, §13.1.
**Depends on:** B5a.
**Blocks:** B5c.

---

## Files

```
/web/app/runs/[id]/page.tsx
/web/components/runs/Timeline.tsx
/web/components/runs/RunHeader.tsx
/web/components/runs/RunStatus.tsx
/web/components/runs/RankedSidebar.tsx           # the live-updating ranked list (right rail)
```

---

## Page layout

Two-column desktop layout: timeline (left, 2/3 width) + ranked sidebar (right, 1/3 width).

```tsx
'use client';

import { use } from "react";
import { useAgentRunStream } from "@/lib/hooks/useAgentRunStream";
import { Timeline } from "@/components/runs/Timeline";
import { RunHeader } from "@/components/runs/RunHeader";
import { RunStatus } from "@/components/runs/RunStatus";
import { RankedSidebar } from "@/components/runs/RankedSidebar";
import { useAgentRun } from "@/lib/hooks/useAgentRun";

export default function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: run } = useAgentRun(id);
  const stream = useAgentRunStream(id);

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <RunHeader run={run} />
      <RunStatus stream={stream} />

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        <section className="lg:col-span-2">
          <h2 className="text-xl font-semibold text-ink mb-4">Agent timeline</h2>
          <Timeline steps={stream.stepOrder.map(id => stream.steps[id])} />
        </section>
        <aside>
          <h2 className="text-xl font-semibold text-ink mb-4">Ranked opportunities</h2>
          <RankedSidebar items={stream.rankedOpportunities} runId={id} />
        </aside>
      </div>
    </main>
  );
}
```

---

## Timeline.tsx

```tsx
import type { StepState } from "@/lib/hooks/useAgentRunStream";
import { StepRow } from "./StepRow";       // from B5c
import { ScrollArea } from "@/components/ui/scroll-area";

export function Timeline({ steps }: { steps: StepState[] }) {
  if (steps.length === 0) {
    return (
      <div className="rounded-md border border-canvas-border bg-canvas-subtle p-6 text-sm text-ink-muted">
        Waiting for the agent to start…
      </div>
    );
  }

  return (
    <ol className="space-y-3" role="list">
      {steps.map((step, i) => (
        <StepRow key={step.step_id} step={step} index={i + 1} />
      ))}
    </ol>
  );
}
```

---

## RunStatus.tsx

Top banner showing run state, cost, elapsed time:

```tsx
import { Badge } from "@/components/ui/badge";
import type { useAgentRunStream } from "@/lib/hooks/useAgentRunStream";
type Stream = ReturnType<typeof useAgentRunStream>;

export function RunStatus({ stream }: { stream: Stream }) {
  const colorByStatus: Record<Stream["status"], string> = {
    idle: "bg-ink-subtle/20",
    connecting: "bg-accent-subtle text-accent",
    streaming: "bg-decision-pursue/15 text-decision-pursue",
    completed: "bg-decision-strong/15 text-decision-strong",
    failed: "bg-decision-reject/15 text-decision-reject",
  };
  return (
    <div className="mt-4 flex items-center gap-4 rounded-md border border-canvas-border p-3 text-sm">
      <span className={`rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wider ${colorByStatus[stream.status]}`}>
        {stream.status}
      </span>
      <span className="text-ink-muted">
        Steps: <span className="text-ink">{stream.stepOrder.length}</span>
      </span>
      <span className="text-ink-muted">
        Cost: <span className="text-ink">${stream.totalCostUsd.toFixed(4)}</span>
      </span>
      {stream.humanQuestion && (
        <span className="ml-auto text-decision-maybe">⚠ Needs review</span>
      )}
    </div>
  );
}
```

---

## RankedSidebar.tsx

Cards collapse to a compact list in the sidebar; full cards live on the results view (B6).

```tsx
import Link from "next/link";
import { DecisionBadge } from "@/components/ui/DecisionBadge";

export function RankedSidebar({
  items, runId,
}: {
  items: { opportunity_id: string; score: number; decision: string }[];
  runId: string;
}) {
  if (!items.length) {
    return <p className="text-sm text-ink-muted">Opportunities appear here as they're scored.</p>;
  }
  return (
    <ul className="space-y-2">
      {items
        .slice()
        .sort((a, b) => b.score - a.score)
        .map(item => (
          <li key={item.opportunity_id}>
            <Link
              href={`/opportunities/${item.opportunity_id}`}
              className="block rounded-md border border-canvas-border bg-canvas p-3 hover:border-accent transition-colors"
            >
              <div className="flex items-center justify-between gap-2">
                <DecisionBadge decision={item.decision as any} score={item.score} />
                <span className="text-xs text-accent">View →</span>
              </div>
              <p className="mt-1 text-xs text-ink-muted">Opportunity {item.opportunity_id.slice(0, 8)}…</p>
            </Link>
          </li>
        ))}
    </ul>
  );
}
```

---

## Animation

When a new step appears, fade-in (~200ms). When status changes from `running` → `complete`, fade the badge color. Use Tailwind's `transition-colors` + `animate-in` from `tailwindcss-animate`.

```tsx
<li className="animate-in fade-in slide-in-from-top-1 duration-200">
```

Disable for `prefers-reduced-motion`.

---

## Done when

- [ ] Replaying example JSONL produces a working live-updating timeline.
- [ ] Each step row is keyboard-navigable; opening the detail expander (B5c) works with mouse and keyboard.
- [ ] RankedSidebar updates as `opportunity_ranked` events arrive; clicking a card navigates to opportunity detail.
- [ ] RunStatus shows cost rolling up live.
- [ ] Empty state appears before first event.
- [ ] After A9 lands, real run produces same visual output.

## Verify

Manual: open `/runs/<mock-id>`, watch the timeline animate as the example JSONL replays.

## Pitfalls

- **Layout shift on new steps.** Reserve space — use `min-h-[X]` on the timeline container so it doesn't jump.
- **Sidebar updates causing re-render of timeline.** Keep them as separate components consuming separate slices of `stream` state.
- **Mobile.** At narrow widths, stack timeline above sidebar, not side-by-side.
- **Long step lists.** > 30 steps gets unwieldy. Use shadcn `scroll-area` to scope vertical scroll inside the timeline, or auto-scroll to newest as it arrives.
