import Link from 'next/link'
import { ArrowRight, Code2, FileJson, Globe, KeyRound } from 'lucide-react'

export const metadata = {
  title: 'GovCapture for agents',
  description:
    'GovCon Bid Desk is a callable capability pack: 10 typed tools any agent can use to find federal contracts, score fit, and produce bid memos.',
}

export default function AgentsPage() {
  return (
    <main className="min-h-screen bg-[#f7f8fb] text-[var(--color-ink)]">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-10 px-5 py-16 sm:px-8">
        <header className="space-y-4">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-[var(--color-accent)]">
            For agents
          </p>
          <h1 className="text-4xl font-semibold tracking-tight">
            Hire a federal contracting capability pack from your agent.
          </h1>
          <p className="max-w-2xl text-base leading-7 text-[var(--color-ink)]">
            GovCon Bid Desk exposes 10 typed tools that find federal
            opportunities, extract requirements, score fit, detect risks,
            and produce bid memos with a human-approval gate. Any
            agent — Claude, GPT, MCP clients, custom workflows — can call
            them over HTTP with a bearer key.
          </p>
        </header>

        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'SoftwareApplication',
              name: 'GovCon Bid Desk',
              applicationCategory: 'BusinessApplication',
              description:
                'Federal contracting capability pack for AI agents. Ten typed tools for SAM search, requirement extraction, fit scoring, risk detection, and bid memo synthesis.',
              offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
              url: 'https://app.govcapture.example/agents',
              operatingSystem: 'Web',
              featureList: [
                'parse-goal', 'parse-pdf', 'extract-requirements',
                'score-fit', 'detect-risks', 'generate-action-package',
                'search-sam', 'fetch-attachment', 'rank-opportunities',
                'load-seeded-opportunities',
              ],
            }),
          }}
        />

        <section className="grid gap-4 sm:grid-cols-2">
          <DiscoveryCard
            icon={<FileJson size={20} />}
            title="Manifest"
            href="/.well-known/agent.json"
            description="Machine-readable description of what's here, where, and how to call it."
          />
          <DiscoveryCard
            icon={<Globe size={20} />}
            title="llms.txt"
            href="/.well-known/llms.txt"
            description="Natural-language summary for AI crawlers — read this before /openapi.json."
          />
          <DiscoveryCard
            icon={<Code2 size={20} />}
            title="OpenAPI"
            href="/openapi.json"
            description="Full JSON Schema for every route. Pair with /docs for Swagger UI."
          />
          <DiscoveryCard
            icon={<KeyRound size={20} />}
            title="Auth"
            href="/app/keys"
            description="Per-agent keys (gck_…) live at /app/keys. Sign in to mint and revoke. Internal callers may continue using X-Internal-API-Key server-to-server."
          />
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">Tools</h2>
          <ul className="grid gap-2 sm:grid-cols-2">
            {TOOLS.map((tool) => (
              <li
                key={tool.name}
                className="rounded-2xl border border-[var(--color-canvas-border)] bg-white p-4"
              >
                <p className="text-sm font-mono text-[var(--color-ink)]">
                  POST /tools/{tool.name}
                </p>
                <p className="mt-1 text-xs text-[var(--color-ink-muted)]">{tool.purpose}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">Quickstart</h2>
          <pre className="overflow-auto rounded-2xl border border-[var(--color-canvas-border)] bg-[var(--color-ink)] p-5 text-xs leading-6 text-slate-100">
{`# Discover
curl https://api.govcapture.example/.well-known/agent.json

# Read llms.txt for the natural-language story
curl https://api.govcapture.example/.well-known/llms.txt

# Read the schemas
curl https://api.govcapture.example/openapi.json | jq '.paths | keys'

# Call a tool (rank a few scored opportunities — pure deterministic)
# Mint $GCK_TOKEN at /app/keys (or use X-Internal-API-Key server-to-server)
curl -X POST https://api.govcapture.example/tools/rank-opportunities \\
  -H "Authorization: Bearer $GCK_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "scored": [
      {"opportunity_id": "a", "decision": "maybe",          "total_score": 60, "due_date": "2026-06-01"},
      {"opportunity_id": "b", "decision": "strong_pursue",  "total_score": 92, "due_date": "2026-06-15"},
      {"opportunity_id": "c", "decision": "pursue",         "total_score": 78, "due_date": "2026-05-20"}
    ]
  }'

# Response (PRD v1.2.6: deterministic skills; no metrics field)
# {"data": {"ranked": [...]}}`}
          </pre>
        </section>

        <section className="space-y-3">
          <h2 className="text-2xl font-semibold tracking-tight">Conventions</h2>
          <ul className="space-y-2 text-sm leading-6 text-[var(--color-ink)]">
            <li>
              All responses share envelope:{' '}
              <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                {`{"data": ...}`}
              </code>
            </li>
            <li>
              Per PRD v1.2.6 every tool is deterministic (mechanics + validators
              only). LLM judgment lives in the calling agent's context; cost +
              token tracking happens there, not in this envelope.
            </li>
            <li>401 on missing or wrong auth header; 422 on malformed payload; 200 on success.</li>
            <li>
              Tool names are stable; new tools may be added. Schema field
              additions are non-breaking; removals/renames bump a major
              version visible in{' '}
              <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                /.well-known/agent.json
              </code>
              .
            </li>
          </ul>
        </section>

        <footer className="border-t border-[var(--color-canvas-border)] pt-6 text-sm text-[var(--color-ink-muted)]">
          <Link
            href="/"
            className="inline-flex items-center gap-1 font-medium text-[var(--color-accent)] underline-offset-4 hover:underline"
          >
            Back to the human-facing site <ArrowRight size={14} aria-hidden />
          </Link>
        </footer>
      </div>
    </main>
  )
}

function DiscoveryCard({
  icon,
  title,
  href,
  description,
}: {
  icon: React.ReactNode
  title: string
  href: string
  description: string
}) {
  return (
    <Link
      href={href}
      className="block rounded-2xl border border-[var(--color-canvas-border)] bg-white p-5 transition hover:border-[var(--color-canvas-border)] hover:bg-slate-50"
    >
      <div className="flex items-center gap-2 text-[var(--color-accent)]">
        {icon}
        <p className="text-sm font-medium">{title}</p>
      </div>
      <p className="mt-2 text-xs leading-5 text-[var(--color-ink-muted)]">{description}</p>
      <p className="mt-3 font-mono text-xs text-[var(--color-ink-muted)]">{href}</p>
    </Link>
  )
}

const TOOLS = [
  { name: 'parse-goal', purpose: 'natural-language goal → structured search criteria' },
  { name: 'parse-pdf', purpose: 'deterministic page-aware PDF text extraction' },
  { name: 'extract-requirements', purpose: 'parsed PDF → §10.1 structured requirements' },
  { name: 'score-fit', purpose: 'company × requirements → fit score; §11.1 short-circuit' },
  { name: 'detect-risks', purpose: '§5.8 risk taxonomy with silent-drop on bad categories' },
  { name: 'generate-action-package', purpose: 'full bid memo or deterministic reject_summary' },
  { name: 'search-sam', purpose: 'SAM.gov v2 search with degraded fallback' },
  { name: 'fetch-attachment', purpose: 'URL → Supabase Storage' },
  { name: 'rank-opportunities', purpose: 'deterministic sort by decision band' },
  { name: 'load-seeded-opportunities', purpose: 'fixture manifests → opportunities table' },
]
