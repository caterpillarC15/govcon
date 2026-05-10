# Wiring this pack into Hermes

The two artifacts Michaela's host needs are (1) the
`mcp-server-samrail` Python package from `mcp_server_samrail/`,
and (2) two keys in `~/.hermes/config.yaml`. Source of authority for
the integration shape: PRD §5.14, `devdocs/CAPABILITY_PACK_INTEGRATION.md`.

## On Michaela's host (Ubuntu 24.04, hostname `govcon`)

```bash
# 1. Hermes MCP extra (one-time)
cd /usr/local/lib/hermes-agent
uv pip install -e ".[mcp]"

# 2. This pack's MCP server
pip install --user "git+https://github.com/caterpillarC15/govcon.git#subdirectory=mcp_server_samrail"
which mcp-server-samrail   # should resolve
```

## `~/.hermes/config.yaml` on her host

```yaml
mcp_servers:
  govcapture:
    command: "mcp-server-samrail"
    env:
      GOVCAPTURE_API_BASE: "https://api.samrail.com"
      GOVCAPTURE_API_KEY: "gck_..."

skills:
  external_dirs:
    - /opt/govcapture-pack/.hermes/skills
```

`gck_…` is minted at `/web → /app/keys` (`POST /api/keys` with a
Supabase JWT also works). The `external_dirs` entry exposes our 5
SKILL.md tool-procedure files (`extract_requirements_with_evidence`,
`score_fit_with_eligibility_check`, `detect_risks_calibrated`,
`generate_full_action_package`, `generate_reject_summary`) without
copying them.

## In her CLI

```
hermes
> /reload-mcp
> /skills
```

`/skills` should list the 5 govcapture procedures. The tool registry
should include 11 entries prefixed `mcp_govcapture_*` (one per
`/api/v1/tools/<name>`).

Smoke test:

```
> /tool mcp_govcapture_parse_goal {"goal":"find SOC contracts in next 60 days","company_profile":{"naics_codes":["541512"]}}
```

Expected: `{"data": {...}}` (no `metrics` field — PRD v1.2.6 dropped
it for non-LLM skills, which is now all of them).

## Network layout

```
Michaela (Hermes v0.13.0, Ubuntu, DeepSeek)
  │  MCP / stdio
  ▼
mcp-server-samrail (Python pkg from this repo, on her box)
  │  HTTPS + Authorization: Bearer gck_…
  ▼
FastAPI /api/v1/tools/<name> (this repo, VX1 prod or local + ngrok)
  │
  ▼
Supabase (vvyxjdoenjujkxwbnzyl) / Redis / fixtures
```

The MCP server is the bridge; the HTTP API is the contract; the `gck_`
key is the auth. She doesn't need source access to this repo.

## Cross-repo coordination owed by `/root/michealaai`

Per `devdocs/CAPABILITY_PACK_INTEGRATION.md` "Three Supabase projects":

1. **Update `/root/michealaai/DATA-SOURCES.md`** to distinguish:
   - `ktygrvbpugqhfyibzirr` — Lance's competitive-intel reads
     (agencies, contractors, contracts, psc_win_patterns,
     customer_profiles)
   - `vvyxjdoenjujkxwbnzyl` — `agent_runs` pickup + writebacks
     (this pack's project; `INTERNAL_API_KEY` writes land here)

   Without this, Michaela polling the wrong project will silently never
   see our `POST /agent-runs` rows.

2. **Mirror `INTERNAL_API_KEY`** between `/opt/govcapture/.env` (VX1
   prod) and `/root/michealaai`'s env on her host. Same string both
   sides, generated once with `openssl rand -hex 32`. The pack's
   `require_internal_actor` rejects mismatches with 401.

## SKILL.md drift check

Michaela's `~/.hermes/skills/samrail/` reportedly contains 8 entries:
the 5 tool-procedure files this repo ships, plus 3 owned by her side
(`analyze_opportunity_e2e`, `discover_opportunities`,
`govcapture-proof-first-voice`). Periodically diff her copy against
`.hermes/skills/samrail/` here:

```bash
# On her host:
ls ~/.hermes/skills/samrail/

# In this repo:
ls .hermes/skills/samrail/
```

If our 5 have drifted from her copies, re-rsync from this repo. Her
3 orchestration recipes are not imported here by design.
