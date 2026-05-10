# mcp-server-samrail

MCP server exposing SamRail's 11 tools. Wraps the pack's public
HTTP surface (`/api/v1/tools/<name>`) — same architectural pattern as the
Hermes plugin (lower latency than reading raw OpenAPI; full type hints).

## Install

    pip install mcp-server-samrail

(Or, while developing this repo:
`uv pip install -e mcp_server_samrail/` from the project root.)

## Configure (Claude Desktop)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or the Windows / Linux equivalent:

```json
{
  "mcpServers": {
    "samrail": {
      "command": "mcp-server-samrail",
      "env": {
        "SAMRAIL_API_KEY": "gck_..."
      }
    }
  }
}
```

Mint a key at https://app.samrail.com/app/keys after sign-in.

`SAMRAIL_API_BASE` defaults to `https://api.samrail.com`. Set
explicitly to point at a dev instance:

```json
"env": {
  "SAMRAIL_API_BASE": "http://localhost:8000",
  "SAMRAIL_API_KEY": "gck_..."
}
```

## Tools

All 11 routes from the pack's `/api/v1/tools/<name>` surface:

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
| `query_usaspending` | USASpending.gov prior-awards lookup with degraded fallback |

Responses share the envelope `{"data": ...}` (PRD v1.2.6 — every
skill is deterministic; no `metrics` field). The wrapper passes the
envelope through unchanged. Cost + token tracking belongs to the
caller, not this pack.

## Rate limits

The pack enforces per-API-key rate limiting (60 requests/minute, refilled
at 1/s). Burst over the cap → HTTP 429 with `Retry-After`.

## Development

```bash
# From the project root.
uv pip install -e mcp_server_samrail/

# Run against a local pack (uvicorn).
SAMRAIL_API_BASE=http://localhost:8000 \
SAMRAIL_API_KEY=$(curl -s -X POST http://localhost:8000/api/keys \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"local-dev"}' | jq -r .plaintext_key) \
mcp-server-samrail
```
