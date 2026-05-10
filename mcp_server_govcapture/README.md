# mcp-server-govcapture

MCP server exposing GovCon Bid Desk's 10 tools. Wraps the pack's public
HTTP surface (`/api/v1/tools/<name>`) — same architectural pattern as the
Hermes plugin (lower latency than reading raw OpenAPI; full type hints).

## Install

    pip install mcp-server-govcapture

(Or, while developing this repo:
`uv pip install -e mcp_server_govcapture/` from the project root.)

## Configure (Claude Desktop)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or the Windows / Linux equivalent:

```json
{
  "mcpServers": {
    "govcapture": {
      "command": "mcp-server-govcapture",
      "env": {
        "GOVCAPTURE_API_KEY": "gck_..."
      }
    }
  }
}
```

Mint a key at https://app.govcapture.example/app/keys after sign-in.

`GOVCAPTURE_API_BASE` defaults to `https://api.govcapture.example`. Set
explicitly to point at a dev instance:

```json
"env": {
  "GOVCAPTURE_API_BASE": "http://localhost:8000",
  "GOVCAPTURE_API_KEY": "gck_..."
}
```

## Tools

All 10 routes from the pack's `/api/v1/tools/<name>` surface:

| Tool | Purpose |
|---|---|
| `parse_goal` | natural-language goal → structured search criteria |
| `parse_pdf` | deterministic page-aware PDF text extraction |
| `extract_requirements` | parsed PDF → §10.1 structured requirements |
| `score_fit` | company × requirements → fit score; §11.1 short-circuit |
| `detect_risks` | §5.8 risk taxonomy with silent-drop on bad categories |
| `generate_action_package` | full bid memo or deterministic reject_summary |
| `search_sam` | SAM.gov v2 search with degraded fallback |
| `fetch_attachment` | URL → Supabase Storage |
| `rank_opportunities` | deterministic sort by decision band |
| `load_seeded_opportunities` | fixture manifests → opportunities table |

Responses share the envelope `{"data": ..., "metrics": LLMMetrics | null}`.
The wrapper passes the envelope through unchanged so the agent sees the
full structure (cost, latency, model on LLM tools).

## Rate limits

The pack enforces per-API-key rate limiting (60 requests/minute, refilled
at 1/s). Burst over the cap → HTTP 429 with `Retry-After`.

## Development

```bash
# From the project root.
uv pip install -e mcp_server_govcapture/

# Run against a local pack (uvicorn).
GOVCAPTURE_API_BASE=http://localhost:8000 \
GOVCAPTURE_API_KEY=$(curl -s -X POST http://localhost:8000/api/keys \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"local-dev"}' | jq -r .plaintext_key) \
mcp-server-govcapture
```
