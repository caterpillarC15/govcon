# B7b — PDF viewer integration + evidence-snippet deep links

**Goal:** Click an evidence snippet → the source PDF opens at the cited `page_number`. **The demo's verifiability moment: every claim traces to a page.**

**PRD references:** §5.10, §13.1.
**Depends on:** B7a.
**Blocks:** B7c.

---

## Files

```
/web/components/opportunities/PdfViewer.tsx           # react-pdf wrapper
/web/components/opportunities/EvidenceLink.tsx        # the clickable snippet
/web/components/opportunities/PdfDialog.tsx           # modal that hosts the viewer
/web/components/opportunities/ConfidenceBadge.tsx
```

Install: `npm install react-pdf` (or `@react-pdf-viewer/core` for richer features).

---

## EvidenceLink.tsx

```tsx
import { useState } from "react";
import { PdfDialog } from "./PdfDialog";
import { Quote } from "lucide-react";

export function EvidenceLink({
  opportunityId, docId, page, snippet,
}: {
  opportunityId: string;
  docId: string;
  page: number;
  snippet: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="mt-2 inline-flex items-start gap-2 rounded-md bg-canvas-subtle px-2 py-1 text-left hover:bg-accent-subtle hover:text-accent transition-colors"
      >
        <Quote className="mt-0.5 h-3 w-3 flex-shrink-0 text-ink-muted" />
        <span className="text-xs italic text-ink leading-5">
          "{snippet.length > 200 ? snippet.slice(0, 197) + "…" : snippet}"
        </span>
        <span className="ml-2 text-xs text-ink-muted whitespace-nowrap">p.{page}</span>
      </button>
      {open && (
        <PdfDialog
          opportunityId={opportunityId}
          docId={docId}
          initialPage={page}
          highlightSnippet={snippet}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}
```

---

## PdfDialog.tsx

```tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { PdfViewer } from "./PdfViewer";

export function PdfDialog({
  opportunityId, docId, initialPage, highlightSnippet, onClose,
}: {
  opportunityId: string;
  docId: string;
  initialPage: number;
  highlightSnippet?: string;
  onClose: () => void;
}) {
  const url = pdfUrl(opportunityId, docId);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{docId}</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-auto">
          <PdfViewer url={url} initialPage={initialPage} highlight={highlightSnippet} />
        </div>
      </DialogContent>
    </Dialog>
  );
}

function pdfUrl(opportunityId: string, docId: string): string {
  // For seeded fixtures: served from /fixtures/<slug>/attachments/<docId>.pdf
  // For live attachments: API endpoint that streams the cached file
  return `${env.NEXT_PUBLIC_API_BASE}/opportunities/${opportunityId}/attachments/${encodeURIComponent(docId)}.pdf`;
}
```

---

## PdfViewer.tsx

```tsx
import { Document, Page, pdfjs } from "react-pdf";
import { useState } from "react";

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

export function PdfViewer({
  url, initialPage = 1, highlight,
}: {
  url: string;
  initialPage?: number;
  highlight?: string;
}) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [page, setPage] = useState(initialPage);

  return (
    <div className="flex flex-col items-center">
      <div className="mb-4 flex items-center gap-3 text-sm">
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page <= 1}
          className="rounded border border-canvas-border px-3 py-1 disabled:opacity-50"
        >
          ←
        </button>
        <span className="tabular-nums">
          Page {page} of {numPages ?? "?"}
        </span>
        <button
          onClick={() => setPage(p => Math.min((numPages ?? p) , p + 1))}
          disabled={!numPages || page >= numPages}
          className="rounded border border-canvas-border px-3 py-1 disabled:opacity-50"
        >
          →
        </button>
      </div>

      <Document file={url} onLoadSuccess={({ numPages }) => setNumPages(numPages)} loading={<p className="text-ink-muted">Loading PDF…</p>}>
        <Page pageNumber={page} width={720} renderTextLayer renderAnnotationLayer={false} />
      </Document>

      {highlight && (
        <p className="mt-4 max-w-2xl rounded-md bg-accent-subtle p-3 text-xs text-ink leading-6">
          <strong className="text-accent">Cited:</strong> "{highlight}"
        </p>
      )}
    </div>
  );
}
```

---

## ConfidenceBadge.tsx

```tsx
const styles: Record<string, string> = {
  high:    "bg-decision-strong/15 text-decision-strong",
  medium:  "bg-decision-pursue/15 text-decision-pursue",
  low:     "bg-decision-maybe/15 text-decision-maybe",
  unknown: "bg-ink-subtle/15 text-ink-muted",
};

export function ConfidenceBadge({ confidence }: { confidence: string }) {
  return (
    <span className={`inline-block flex-shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${styles[confidence]}`}>
      {confidence}
    </span>
  );
}
```

---

## API endpoint for fixture PDFs

A serves these from local FS (seeded fixtures) or from the cache (live attachments). The route:

```
GET /opportunities/:id/attachments/:filename
```

For seeded: looks up the fixture slug from the opportunity's `source_document`, returns the file from `/fixtures/<slug>/attachments/<filename>`. Coordinate with A.

CORS must allow your Vercel origin (and `localhost:3000`).

---

## Highlight (stretch)

Visually highlighting the cited snippet inside the PDF is hard with `react-pdf`'s default text layer. Two options:

1. **Show snippet next to PDF** (current implementation). Simpler, ships v1.
2. **Highlight in the text layer** using `react-pdf-highlighter` or custom overlay logic. Stretch.

For the hackathon, option 1 is plenty. The user sees the page AND the snippet — verifiability achieved.

---

## Done when

- [ ] Click an evidence snippet on any requirement → modal opens with the source PDF on the cited page.
- [ ] Page navigation works.
- [ ] On the reject fixture, clicking the clearance-blocker evidence opens the PDF on page 2 with the blocker text shown next to the viewer. **This is a stage moment — practice it.**
- [ ] Closing the modal returns focus to the snippet button (a11y).

## Verify

Click each of the strong-pursue fixture's medium/high confidence requirements → confirm PDF opens at cited page. Then the reject fixture — confirm the clearance evidence is on page 2.

## Pitfalls

- **`pdfjs` worker not loading.** The CDN URL must match the installed version. If it 404s, the viewer hangs forever. Use exact-version pinning.
- **CORS blocking the PDF fetch.** Cross-origin PDF loads need explicit headers. Test with curl + browser network tab.
- **Mobile viewer is unusable.** That's OK for demo (we're on a laptop). Document as a known limitation.
- **Page number off-by-one.** `react-pdf` is 1-indexed. Our schema is 1-indexed. Stay consistent; don't subtract.
