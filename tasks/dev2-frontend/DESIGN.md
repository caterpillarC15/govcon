# Design Notes

UI tokens, layout patterns, and component conventions for the GovCapture web app. Keep it spare and document-grade — this is a tool a small business owner uses to make a decision, not a dashboard contest.

---

## Aesthetic direction

- **Document-feel, not dashboard-feel.** Single-column reading flow for the action package. Tight line-height. Generous whitespace.
- **Trust signals are visible.** Source-citation links, evidence snippets, decision rationale — always one click away.
- **No dark theme for v1.** Save the bandwidth. Light theme only.
- **Federal-government appropriate.** Quiet palette. No garish gradients. No animated illustrations. Color exists to encode meaning, not decoration.
- **Typography drives hierarchy.** Don't lean on heavy borders or shadows.

---

## Color tokens

Tailwind config — extend the default palette. Use semantic names so we can re-skin later.

```ts
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        // Brand
        ink: {
          DEFAULT: "#0f172a",   // primary text (slate-900)
          muted: "#475569",     // secondary text (slate-600)
          subtle: "#94a3b8",    // tertiary (slate-400)
        },
        canvas: {
          DEFAULT: "#ffffff",
          subtle: "#f8fafc",    // section background (slate-50)
          border: "#e2e8f0",    // borders (slate-200)
        },
        accent: {
          DEFAULT: "#1e3a8a",   // navy 800 — federal-y, trustworthy
          hover: "#1e40af",     // navy 700
          subtle: "#dbeafe",    // navy 100 — for highlight bands
        },
        // Decision bands
        decision: {
          strong: "#15803d",    // green 700
          pursue: "#1e40af",    // navy 700
          maybe: "#b45309",     // amber 700
          reject: "#b91c1c",    // red 700
        },
        // Severity
        severity: {
          critical: "#b91c1c",
          major: "#c2410c",     // orange 700
          moderate: "#b45309",  // amber 700
          minor: "#475569",     // slate 600
        },
        // Status (for compliance matrix)
        status: {
          met: "#15803d",
          missing: "#b91c1c",
          unclear: "#b45309",
          na: "#94a3b8",
        },
      },
      fontFamily: {
        sans: ["Inter Variable", "ui-sans-serif", "system-ui"],
        serif: ["Source Serif 4", "ui-serif", "Georgia"],   // for the action package "document" feel
        mono: ["JetBrains Mono Variable", "ui-monospace"],
      },
    },
  },
};
```

Use Tailwind classes everywhere; no inline `style={}` for colors.

---

## Typography rules

| Element | Class |
|---------|-------|
| Page title | `text-3xl font-semibold tracking-tight text-ink` |
| Section heading | `text-xl font-semibold text-ink` |
| Subsection heading | `text-base font-semibold text-ink` |
| Body | `text-sm leading-6 text-ink` (15px on Retina; readable) |
| Muted/meta | `text-xs text-ink-muted` |
| Action-package body (document mode) | `text-base leading-7 text-ink font-serif` — yes, serif |
| Decision badge | `text-xs font-semibold uppercase tracking-wider` |

---

## Layout patterns

**Full-width pages with constrained content:**

```tsx
<main className="mx-auto max-w-4xl px-6 py-12">
  {/* content */}
</main>
```

For the run timeline (B5b), use `max-w-5xl`. For the action package (B8), use `max-w-3xl` so it reads like a document.

**Section dividers:**

```tsx
<div className="border-t border-canvas-border my-10" />
```

**Cards** (opportunity cards, B6):

```tsx
<article className="rounded-lg border border-canvas-border bg-canvas p-6 hover:border-accent transition-colors">
  {/* card content */}
</article>
```

No drop-shadows on cards. Borders only.

---

## Decision badges

Reusable component used on every opportunity reference:

```tsx
const colors: Record<Decision, string> = {
  strong_pursue: "bg-decision-strong/10 text-decision-strong border-decision-strong/30",
  pursue:        "bg-decision-pursue/10 text-decision-pursue border-decision-pursue/30",
  maybe:         "bg-decision-maybe/10 text-decision-maybe border-decision-maybe/30",
  reject:        "bg-decision-reject/10 text-decision-reject border-decision-reject/30",
};

const labels: Record<Decision, string> = {
  strong_pursue: "Strong pursue",
  pursue: "Pursue",
  maybe: "Maybe",
  reject: "Reject",
};

export function DecisionBadge({ decision, score }: { decision: Decision; score?: number }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded border px-2 py-0.5 text-xs font-semibold uppercase tracking-wider ${colors[decision]}`}>
      {labels[decision]}
      {score !== undefined && <span className="text-ink-muted font-normal normal-case">{score}/100</span>}
    </span>
  );
}
```

---

## Status pills (compliance matrix)

```tsx
const statusStyles = {
  met:            "bg-status-met/10 text-status-met",
  missing:        "bg-status-missing/10 text-status-missing",
  unclear:        "bg-status-unclear/10 text-status-unclear",
  not_applicable: "bg-status-na/10 text-status-na",
};
```

Pills are small (`text-xs px-2 py-0.5 rounded-full`). Always include the literal status word (don't rely on color alone — accessibility).

---

## Severity colors (risk register)

Same family but for risks. Use a left-border accent, not full-fill:

```tsx
<div className={`border-l-4 pl-4 ${{
  critical_blocker: "border-severity-critical bg-severity-critical/5",
  major: "border-severity-major bg-severity-major/5",
  moderate: "border-severity-moderate bg-severity-moderate/5",
  minor: "border-severity-minor",
}[severity]}`}>
  {/* risk content */}
</div>
```

---

## Approval gate (PRD §5.13)

Visually unmissable. Top of action-package page. Sticky on scroll if possible.

```tsx
<div className="rounded-lg border-2 border-decision-reject/40 bg-decision-reject/5 p-4 mb-6">
  <h3 className="text-base font-semibold text-decision-reject">⚠ Human approval required</h3>
  <p className="mt-2 text-sm text-ink">
    Do not send emails, submit materials, claim certifications, or mark compliance complete without authorized review.
  </p>
  <ul className="mt-3 space-y-1 text-sm text-ink">
    {package.human_approval_required.map((item, i) => (
      <li key={i} className="flex gap-2"><span className="text-ink-muted">•</span>{item}</li>
    ))}
  </ul>
</div>
```

Use the reject color for the warning vibe — it's an attention-grabber, even on packages with `decision="strong_pursue"`.

---

## Loading and empty states

- **Loading:** skeleton shapes that match the eventual layout. Don't use spinners for content.
- **Empty:** short, useful sentence + a clear next action. "No opportunities yet — start a capture run from your profile page."
- **Failed:** plain language + retry button. "We couldn't reach the agent. Try again — your draft is saved."

---

## Animations

Minimal. Prefer fades over slides. Timeline events animate in (~200ms fade) but that's it. No bouncing, no parallax, no scroll-triggered reveals.

Tailwind's `transition-colors` for hover states. Use `prefers-reduced-motion` to disable everything.

---

## Component inventory

Add components to shadcn as you need them. Expected for v1:

- `button`, `card`, `input`, `textarea`, `label`, `badge`, `separator`
- `dialog` (for needs_human modals, paste-import in profile)
- `scroll-area` (for the timeline)
- `tooltip` (for evidence-snippet hover)
- `sonner` (toast notifications — for "outreach copied", "package exported")
- `tabs` (opportunity detail sections, possibly)
- `accordion` (timeline step expansion — alternative to custom)

Don't install components you don't use. shadcn copies into your repo, so each install is a commit.

---

## Print stylesheet (B8 export)

The action package supports `window.print()`. Tailwind's `print:` variants make this easy:

```tsx
<main className="mx-auto max-w-3xl p-12 print:p-0 print:max-w-none">
  <header className="mb-8 print:mb-4">
    {/* ... */}
  </header>
</main>
```

Hide UI chrome on print: nav, action buttons, the approval gate's warning style (replace with a print-friendly disclaimer).

```tsx
<nav className="print:hidden">...</nav>
<div className="approval-gate print:border print:bg-white">...</div>
```

---

## Accessibility

- Every interactive element has a visible focus ring (`focus-visible:ring-2 focus-visible:ring-accent`).
- Decision badges include the text label, not just color.
- The PDF viewer has a "page X of Y" indicator and keyboard navigation (`react-pdf` provides hooks).
- Forms have proper `<label htmlFor>` associations.
- The timeline is a list (`<ol>` with `role="list"`); each step is a list item.

---

## What NOT to design

- A landing page with marketing copy. The user enters at the profile page; everything is interior.
- A dashboard with metrics widgets. We're not analytics.
- A multi-tenant onboarding. PRD §17 Q4: single profile per session for MVP.
- A dark theme.
- Custom illustrations. shadcn icons (lucide-react) are sufficient.
