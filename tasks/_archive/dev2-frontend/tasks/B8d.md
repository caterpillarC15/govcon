# B8d — Outreach draft + export/print controls

**Goal:** PRD §5.11 — outreach draft (subject/body) with copy-to-clipboard, plus export controls (print, JSON download). Optional stretch: server-rendered PDF.

**PRD references:** §5.11, §5.13.
**Depends on:** B8a, B8b, B8c.
**Blocks:** B14 (demo rehearsal).

---

## Files

```
/web/components/packages/OutreachDraft.tsx
/web/components/packages/ExportControls.tsx
```

---

## OutreachDraft.tsx

```tsx
import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";
import type { ActionPackage } from "@/lib/schemas";

export function OutreachDraft({ draft }: { draft: ActionPackage["outreach_draft"] }) {
  const [copiedSubject, setCopiedSubject] = useState(false);
  const [copiedBody, setCopiedBody] = useState(false);
  const [copiedAll, setCopiedAll] = useState(false);

  if (!draft || (!draft.subject && !draft.body)) return null;

  const copyAll = async () => {
    await navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`);
    toast.success("Outreach copied to clipboard");
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 1500);
  };

  return (
    <section className="mt-12">
      <h2 className="text-xl font-semibold text-ink">Outreach draft</h2>
      <p className="mt-2 text-sm text-ink-muted">
        Suggested first contact. <strong className="text-ink">Human approval required before sending.</strong>
      </p>

      <div className="mt-4 rounded-md border border-canvas-border bg-canvas">
        <div className="flex items-center justify-between border-b border-canvas-border px-4 py-2">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-ink-muted">Subject:</span>
            <span className="text-ink">{draft.subject}</span>
          </div>
          <button
            onClick={async () => {
              await navigator.clipboard.writeText(draft.subject);
              setCopiedSubject(true);
              setTimeout(() => setCopiedSubject(false), 1500);
            }}
            className="text-xs text-accent hover:underline flex items-center gap-1"
          >
            {copiedSubject ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            {copiedSubject ? "Copied" : "Copy"}
          </button>
        </div>

        <div className="px-4 py-3">
          <pre className="whitespace-pre-wrap text-sm text-ink leading-6 font-serif">{draft.body}</pre>
        </div>

        <div className="border-t border-canvas-border px-4 py-2 flex items-center justify-end gap-3">
          <button
            onClick={async () => {
              await navigator.clipboard.writeText(draft.body);
              setCopiedBody(true);
              setTimeout(() => setCopiedBody(false), 1500);
            }}
            className="text-xs text-accent hover:underline flex items-center gap-1"
          >
            {copiedBody ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            Copy body
          </button>
          <button
            onClick={copyAll}
            className="rounded-md bg-accent px-3 py-1 text-xs font-medium text-canvas hover:bg-accent-hover flex items-center gap-1"
          >
            {copiedAll ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            Copy subject + body
          </button>
        </div>
      </div>

      <p className="mt-3 text-xs text-ink-muted">
        Recipient name not included — fill in before sending. The agent does not invent contacts.
      </p>
    </section>
  );
}
```

---

## ExportControls.tsx

```tsx
import { Download, Printer, FileJson } from "lucide-react";
import type { ActionPackage } from "@/lib/schemas";

export function ExportControls({ pkg }: { pkg: ActionPackage }) {
  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(pkg, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `action-package-${pkg.id ?? "export"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="mt-16 border-t border-canvas-border pt-6 print:hidden">
      <h2 className="text-base font-semibold text-ink">Export</h2>
      <div className="mt-3 flex flex-wrap gap-3">
        <button
          onClick={() => window.print()}
          className="inline-flex items-center gap-2 rounded-md border border-canvas-border bg-canvas px-3 py-2 text-sm hover:border-accent"
        >
          <Printer className="h-4 w-4" />
          Print / save as PDF
        </button>
        <button
          onClick={downloadJson}
          className="inline-flex items-center gap-2 rounded-md border border-canvas-border bg-canvas px-3 py-2 text-sm hover:border-accent"
        >
          <FileJson className="h-4 w-4" />
          Download JSON
        </button>
      </div>
      <p className="mt-3 text-xs text-ink-muted">
        Browser print-to-PDF works for v1. Server-side PDF export is post-MVP.
      </p>
    </section>
  );
}
```

---

## Server-side PDF (stretch, post-MVP)

If time permits later: API route that uses `weasyprint` or `playwright.pdf()` to render the action package server-side. For v1, browser print is sufficient.

---

## Print stylesheet (final pass)

Add to `globals.css`:

```css
@media print {
  body { background: white; color: black; }
  .print\\:hidden { display: none !important; }

  table { page-break-inside: auto; }
  tr { page-break-inside: avoid; }

  h1, h2, h3 { break-after: avoid; }
  section { break-inside: avoid-page; }
}

@page {
  margin: 1in;
}
```

---

## Done when

- [ ] Strong-pursue: outreach draft visible, copy-to-clipboard works (toast confirms).
- [ ] Reject: outreach section hidden (per A8 reject path).
- [ ] Print preview renders document-grade — no chrome, no buttons.
- [ ] JSON download works.
- [ ] Toast notifications fire on copy.
- [ ] All approval-gate language remains visible in print.

## Verify

1. Open strong-pursue action package.
2. Click "Copy subject + body" → toast appears.
3. Paste into a notes app → confirm format `Subject: ...\n\nBody...`.
4. Cmd+P → preview should look document-grade.
5. Click "Download JSON" → file lands in Downloads.

## Pitfalls

- **Toast notifications missing in production.** Verify `<Toaster />` is mounted in `app/layout.tsx`.
- **Copy permissions in some browsers.** Mobile Safari sometimes blocks `navigator.clipboard.writeText` outside user-gesture context. We're inside a click handler, should be fine.
- **`window.print()` triggering twice.** Some setups double-fire on click. Debounce if needed.
- **`pre.whitespace-pre-wrap` with very long lines.** Use `break-words` to avoid horizontal scroll.
