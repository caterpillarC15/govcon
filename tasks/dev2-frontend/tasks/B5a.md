# B5a — SSE consumer + typed event union

**Goal:** A reusable hook that consumes the agent run SSE stream and exposes events as a typed discriminated union. Built against `/schemas/trace-event.example.jsonl` until A9 lands.

**PRD references:** §5.3, CONTRACTS.md §3.
**Depends on:** B2 (zod schemas, env).
**Blocks:** B5b.

---

## Files

```
/web/lib/hooks/useAgentRunStream.ts        # the hook
/web/lib/sse.ts                             # already in B2; refine here
/web/lib/trace-events.ts                    # event constant table + helpers
```

(Most of the consumer is in B2's `useAgentRunStream`; this task hardens it.)

---

## Refinements over B2's draft

The B2 hook works but is naive. For B5b's UI to render correctly we need:

1. **Per-step grouping** — events arrive in sequence; we want to group them by `step_id` so the UI can render one row per step with its tool calls nested.
2. **Replay mode** — for dev when the backend isn't running, replay the example JSONL.
3. **Reconnect logic** — if the SSE drops mid-run, reconnect once.
4. **Performance** — events are small, but a long run could emit 100+ events. Avoid causing a re-render storm.

---

## Skeleton

```ts
import { useEffect, useReducer, useRef } from "react";
import { env } from "@/lib/env";
import { TraceEventSchema, type TraceEvent } from "@/lib/schemas";

const TRACE_EVENT_TYPES = [
  "run_started", "step_started", "tool_called", "tool_returned",
  "step_completed", "opportunity_ranked", "needs_human", "run_completed",
] as const;

type StepState = {
  step_id: string;
  label: string;
  status: "running" | "complete" | "degraded" | "failed" | "needs_review";
  toolCalls: { tool: string; rationale?: string; input?: unknown; output?: unknown; error?: string; latency_ms?: number; cost_usd?: number }[];
  startedAt: string;
};

type State = {
  status: "idle" | "connecting" | "streaming" | "completed" | "failed";
  events: TraceEvent[];
  steps: Record<string, StepState>;       // by step_id
  stepOrder: string[];                    // insertion order for rendering
  rankedOpportunities: { opportunity_id: string; score: number; decision: string }[];
  humanQuestion: { question: string; context: unknown } | null;
  totalCostUsd: number;
};

const initial: State = {
  status: "idle",
  events: [],
  steps: {},
  stepOrder: [],
  rankedOpportunities: [],
  humanQuestion: null,
  totalCostUsd: 0,
};

type Action =
  | { type: "open" }
  | { type: "close"; success: boolean }
  | { type: "event"; event: TraceEvent };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "open": return { ...state, status: "streaming" };
    case "close": return { ...state, status: action.success ? "completed" : "failed" };
    case "event": {
      const ev = action.event;
      const events = [...state.events, ev];

      switch (ev.type) {
        case "step_started": {
          const step: StepState = {
            step_id: ev.step_id, label: ev.label, status: "running", toolCalls: [], startedAt: ev.ts,
          };
          return { ...state, events,
            steps: { ...state.steps, [ev.step_id]: step },
            stepOrder: [...state.stepOrder, ev.step_id],
          };
        }
        case "tool_called": {
          const step = state.steps[ev.step_id];
          if (!step) return { ...state, events };
          const updated: StepState = {
            ...step,
            toolCalls: [...step.toolCalls, { tool: ev.tool, rationale: ev.rationale, input: ev.input }],
          };
          return { ...state, events, steps: { ...state.steps, [ev.step_id]: updated } };
        }
        case "tool_returned": {
          const step = state.steps[ev.step_id];
          if (!step) return { ...state, events };
          const last = step.toolCalls[step.toolCalls.length - 1];
          const merged = { ...last, output: ev.output, error: ev.error, latency_ms: ev.latency_ms, cost_usd: ev.cost_usd };
          const newCalls = [...step.toolCalls.slice(0, -1), merged];
          return { ...state, events,
            steps: { ...state.steps, [ev.step_id]: { ...step, toolCalls: newCalls } },
            totalCostUsd: state.totalCostUsd + (ev.cost_usd ?? 0),
          };
        }
        case "step_completed": {
          const step = state.steps[ev.step_id];
          if (!step) return { ...state, events };
          return { ...state, events,
            steps: { ...state.steps, [ev.step_id]: { ...step, status: ev.status as StepState["status"] } },
          };
        }
        case "opportunity_ranked":
          return { ...state, events, rankedOpportunities: [...state.rankedOpportunities, {
            opportunity_id: ev.opportunity_id, score: ev.score, decision: ev.decision,
          }] };
        case "needs_human":
          return { ...state, events, humanQuestion: { question: ev.question, context: ev.context } };
        case "run_started":
        case "run_completed":
          return { ...state, events, status: ev.type === "run_completed" ? "completed" : "streaming" };
      }
    }
  }
}

export function useAgentRunStream(runId: string | null) {
  const [state, dispatch] = useReducer(reducer, initial);
  const reconnectsRef = useRef(0);

  useEffect(() => {
    if (!runId) return;
    let closed = false;

    const connect = () => {
      const es = new EventSource(`${env.NEXT_PUBLIC_API_BASE}/agent-runs/${runId}/stream`);
      es.onopen = () => dispatch({ type: "open" });
      es.onerror = () => {
        if (closed) return;
        es.close();
        if (reconnectsRef.current < 1) {
          reconnectsRef.current += 1;
          setTimeout(connect, 1500);
        } else {
          dispatch({ type: "close", success: false });
        }
      };

      for (const t of TRACE_EVENT_TYPES) {
        es.addEventListener(t, (msg: MessageEvent) => {
          try {
            const data = JSON.parse(msg.data);
            const parsed = TraceEventSchema.safeParse(data);
            if (parsed.success) dispatch({ type: "event", event: parsed.data });
            else if (process.env.NODE_ENV !== "production") {
              console.warn("Invalid trace event:", parsed.error.format(), data);
            }
          } catch (e) {
            console.warn("Failed to parse trace event:", e, msg.data);
          }
          if ((JSON.parse(msg.data) as TraceEvent).type === "run_completed") {
            dispatch({ type: "close", success: true });
            es.close();
          }
        });
      }

      return () => es.close();
    };

    const cleanup = connect();
    return () => { closed = true; cleanup(); };
  }, [runId]);

  return state;
}
```

---

## Replay-mode helper

For dev when the backend's down:

```ts
// /web/lib/dev/replayTrace.ts
export async function replayExampleTrace(onEvent: (e: TraceEvent) => void): Promise<void> {
  const res = await fetch("/dev/trace-event.example.jsonl");
  const text = await res.text();
  const lines = text.trim().split("\n");
  let prevTs: number | null = null;
  for (const line of lines) {
    const event = JSON.parse(line) as TraceEvent;
    const t = new Date(event.ts).getTime();
    if (prevTs !== null) {
      await new Promise(r => setTimeout(r, Math.max(100, t - prevTs)));
    }
    prevTs = t;
    onEvent(event);
  }
}
```

Copy `/schemas/trace-event.example.jsonl` to `/web/public/dev/` so it's fetchable from the browser.

---

## Done when

- [ ] Replaying the example JSONL (via mock SSE or `replayExampleTrace`) produces a correct `state` with all 8 event types accounted for.
- [ ] Steps group correctly by `step_id`; tool calls land in the right step; `tool_returned` merges into the previous `tool_called`.
- [ ] Reconnect on transient error works once, then surfaces failed state.
- [ ] `totalCostUsd` accumulates across all `tool_returned` events.
- [ ] No re-render storms — useReducer dispatches are batched per event.
- [ ] `tsc --noEmit` passes; the discriminated union switch is exhaustive.

## Verify

```bash
# With mock server replaying example JSONL:
cd web && npm run dev
# Open /runs/<mock-id>; watch React Devtools state tree; confirm steps populate.

# Or run the replay helper from a dev page:
# 1. add a /dev/replay route that calls replayExampleTrace and renders state
# 2. confirm cadence is human-readable
```

## Pitfalls

- **Forgetting to `.close()` the EventSource on unmount.** Memory leak + zombie connections. Cleanup function returns `() => es.close()`.
- **Reducer non-exhaustive switch.** TypeScript doesn't enforce discriminated-union exhaustiveness without an explicit `never` branch. Add one.
- **`run_completed` arriving before `step_completed` for the last step.** Possible if the API emits run-end before flushing per-step updates. Tolerate gracefully — don't assume order beyond per-step.
- **Browser tab throttling.** Background tabs throttle setTimeout, which makes the replay mode look weird. Document for testers.
