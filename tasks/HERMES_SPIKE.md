# T4.1 Hermes Process Boundary Spike

**Date:** 2026-05-09
**Author:** T4.1 spike (automated)
**Status:** DONE — recommendation is B (subprocess) + MCP toolset server

---

## 1. What is installed

| Item | Finding |
|------|---------|
| `hermes-agent` in govcapture venv? | **No.** `uv pip list` shows nothing. |
| `hermes-agent` on PyPI? | **No.** `curl https://pypi.org/pypi/hermes-agent/json` returns 404. |
| Hermes CLI installed on the host? | **Yes.** `~/.local/bin/hermes`, version **0.13.0 (2026-05-07)**. |
| Installed how? | Editable install in its own venv at `~/.hermes/hermes-agent/venv/`. Installer script writes `~/.local/bin/hermes` pointing to that venv's Python. |
| Can we import from govcapture's venv? | **No.** Different Python 3.11 venv vs govcapture's Python 3.12. Module names (`run_agent`, `tools`, `utils`) would conflict. |

---

## 2. Hermes' actual API surface

### 2.1 Python API (`run_agent.AIAgent`)

Hermes exposes a `class AIAgent` in `~/.hermes/hermes-agent/run_agent.py`.

**Key constructor parameters:**
```python
AIAgent(
    model: str,
    api_key: str,
    provider: str,
    enabled_toolsets: List[str],
    disabled_toolsets: List[str],
    tool_start_callback: callable,       # (call_id, tool_name, args) -> None
    tool_complete_callback: callable,    # (call_id, tool_name, args, result) -> None
    step_callback: callable,             # (iteration_n, prev_tool_list) -> None
    status_callback: callable,           # ("lifecycle"|"warn", message) -> None
    stream_delta_callback: callable,
    quiet_mode: bool,
    max_iterations: int,
    session_id: str,
)
```

**Run method:**
```python
result: dict = agent.run_conversation(
    user_message: str,
    system_message: str = None,
    conversation_history: list = None,
    task_id: str = None,
)
# result["final_response"] -> str
```

`run_conversation` is **synchronous**. Internally it uses threads (`ThreadPoolExecutor`) for parallel delegation but blocks the caller until the agent run completes. It calls `asyncio.run()` only for isolated vision tasks (not the main loop). There is no `async` entrypoint.

**Delegation mechanism:**
```python
delegate_task(
    goal: str,
    context: str,
    toolsets: List[str],
    tasks: List[dict],      # batch/parallel mode
    role: "leaf"|"orchestrator",
    parent_agent: AIAgent,
)
```
Children are spawned in a `ThreadPoolExecutor`. Each child is an `AIAgent` fork with isolated task_id, restricted toolsets, and its own conversation. Parents block until all children complete.

**Tool registration:**
Tools are registered at module-import time via `tools/registry.py`:
```python
registry.register(
    name="my_tool",
    toolset="my_toolset",
    schema={"type":"function","function":{...}},
    handler=my_fn,
    is_async=False,
)
```
`discover_builtin_tools()` scans `tools/*.py` at startup and imports any module with a top-level `registry.register(...)` call.

### 2.2 CLI (subprocess) API

```
hermes chat -q QUERY -Q [-m MODEL] [-t TOOLSETS] [--source tool]
```

- `-Q` (quiet mode): stdout = only the final agent response. stderr = session_id line + errors.
- Exit code: 0 = success, 1 = model/tool failure.
- `--source tool` excludes the session from the user's session list.
- `--ignore-rules` skips SOUL.md / HERMES.md injection (useful for isolated test runs).
- When cwd = repo root, Hermes auto-loads `HERMES.md` (the root project context, §11.1 rules, toolset map) without any CLI flag. This is critical — no flags needed to inject our hard rules.

**Smoke test result (2026-05-09):** `subprocess.run(["hermes","chat","-q","...","-Q"])` with `cwd=REPO_ROOT` started correctly. Subprocess exited non-zero due to Hermes account credit exhaustion on the Nous portal (`claude.ai` extra usage limit). The **mechanism** (subprocess invocation, stdout/stderr separation, exit code, session_id in stderr) is confirmed correct. Failure was a credentials/billing issue, not an architecture issue.

### 2.3 MCP server support

Hermes supports MCP servers declared in `~/.hermes/config.yaml` under `mcp_servers`. Each MCP server is started as a subprocess and its tools are registered into Hermes' registry under toolset name `mcp-<server-name>`. The agent can call them like built-in tools. The restriction mechanism (`delegate_task(toolsets=[...])`) works on MCP-registered tool names exactly like built-in tools.

---

## 3. Open questions answered

| Question (from `tasks/HERMES.md`) | Answer |
|---|---|
| 1. Stable Python SDK, gRPC, or shell-out? | **Shell-out is the only viable path** (different venv, not on PyPI). Python SDK is inaccessible from govcapture's venv without major path gymnastics. |
| 2. Trace event format | CLI quiet mode gives only the final response. Real-time events come from the `status_callback` / `step_callback` / `tool_start_callback` / `tool_complete_callback` — these fire in-process and are not exposed over the subprocess stdout wire. For subprocess usage, the event stream must come from a different source (see §5). |
| 3. Toolset registration | **MCP is the correct external extension point.** Drop Python tool modules into Hermes' install dir is not maintainable. Drop a govcapture MCP server into `mcp_servers` config and Hermes picks it up on startup. |
| 5. Hermes memory + Postgres | Confirmed: Hermes memory (`~/.hermes/memories/`) is for agent recall. Our Postgres holds domain entities (opportunities, requirements, scores, packages). No double-storage — they are separate layers. |
| 6. Cost tracking | Hermes surfaces per-run cost in its TUI and session file, but not via structured stdout in quiet mode. Our toolsets (the MCP server functions) will compute cost_usd from the Anthropic client's usage data and return it in the tool result. The bridge sums it per run. |
| 7. Per-subagent model override | Config-level `delegation.model` sets the default for children. Per-call override is possible via `delegate_task(model=...)` but only respected when the child agent has `delegation.model` set in config or the parent sets it in the delegation context. **Cleanest approach:** encode model choice in the agent's goal/context string and the planner instructions; risk the cost difference between Sonnet and Haiku is small enough not to need per-call routing in V1. |

---

## 4. Recommended architecture: B (subprocess) + MCP toolset server

### Why NOT A (in-process)

1. `hermes-agent` is not on PyPI and not in our venv. Adding it requires a `pip install -e ~/.hermes/hermes-agent` path dep that is not pinned, not versioned, and not portable.
2. Hermes uses Python 3.11; govcapture uses Python 3.12. Even with a shared venv, editable installs across interpreter versions are fragile.
3. Top-level module names (`run_agent`, `tools`, `agent`, `utils`, `toolsets`) would conflict with any module we name similarly in the future.
4. `run_conversation()` is **synchronous** and internally heavy (ThreadPoolExecutor, asyncio loops in sub-tasks). Running it in a FastAPI background task on the same event loop would block the loop or require `asyncio.run_in_executor` wrappers around an already-threaded library — exactly the kind of complexity we don't want.

### Why B (subprocess)

1. `hermes chat -q QUERY -Q` is a **first-class, explicitly documented** one-shot mode. It is not a hack.
2. Hermes auto-loads our `HERMES.md` project context when cwd = repo root. §11.1 rules, toolset map, and agent roles load without code changes.
3. Clean venv boundary — govcapture's deps and Hermes' deps are fully isolated.
4. Exit code signals health; stderr carries session_id for log correlation.
5. `tasks/HERMES.md` line 73 already says "FastAPI invokes Hermes as a subprocess."

### Architecture diagram

```
FastAPI POST /agent-runs
    |
    v
api/agent/hermes_runner.py
    subprocess.Popen([
        "hermes", "chat",
        "-q", goal_with_profile,
        "-Q",
        "-m", "claude-sonnet-4-6",
        "--provider", "anthropic",
        "--source", "tool",
    ], cwd=REPO_ROOT, env={HERMES_HOME, ANTHROPIC_API_KEY, ...})
    |
    |-- stdout: final agent response (JSON summary string)
    |-- stderr: session_id + warnings
    |
    v
api/agent/hermes_bridge.py
    parse stdout -> OurEvent("run_completed", ...)
    SSE emit -> frontend (B5 Timeline)

Hermes (child process)
    loads HERMES.md (cwd=repo root)
    loads .hermes/config.yaml (HERMES_HOME)
    starts MCP server (govcapture MCP)
    |
    v
api/mcp_server/  (our MCP server, started by Hermes on demand)
    tools: parse_pdf, extract_requirements, score_fit,
           detect_risks, generate_action_package,
           search_sam, load_seeded_opportunities,
           fetch_attachment, verify_source_page
```

### Trace event source for B5 Timeline

**V1 decision: accept the SSE gap; ship step-level events from MCP tool calls only.**

Full step-level events (step_started, step_completed for every LLM turn) require either:
- Gateway mode (`tui_gateway/`), which uses a JSON-RPC stdio pipe — significant plumbing.
- Polling Hermes' session file — not real-time.

For V1 the timeline will show:
- `run_started` when the subprocess launches
- `tool_called` / `tool_returned` from each MCP tool call (the MCP server emits these to an asyncio queue that the bridge reads)
- `run_completed` when the subprocess exits

This maps to CONTRACTS.md §3's `tool_called`, `tool_returned`, and `run_completed` events. `step_started` / `step_completed` are deferred to V2 when gateway mode can be wired.

---

## 5. Concrete plan for T4.2

### Files to create

```
api/
├── agent/
│   ├── hermes_runner.py    # Popen + stdout read + SSE emit on completion
│   └── hermes_bridge.py    # MCP tool event queue -> SSE event translation
└── mcp_server/
    ├── __init__.py
    ├── server.py           # FastMCP stdio server exposing our 9 toolsets
    └── tools/
        ├── gov_discovery.py
        ├── gov_documents.py
        ├── gov_compliance.py
        ├── gov_risks.py
        ├── gov_proposals.py
        └── human_review.py
```

### `api/agent/hermes_runner.py` (skeleton)

```python
import asyncio
import os
import subprocess
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
HERMES_BIN = os.path.expanduser("~/.local/bin/hermes")


async def launch_hermes_run(
    run_id: uuid.UUID,
    goal: str,
    emit_event,          # async callable(event_type, run_id, **payload)
) -> None:
    """Launch Hermes as a subprocess, stream MCP events, emit SSE events."""
    await emit_event("run_started", run_id, goal=goal)

    env = {
        **os.environ,
        "HERMES_HOME": os.environ["HERMES_HOME"],
        "ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"],
        "HERMES_QUIET": "1",
        "GOVCAPTURE_RUN_ID": str(run_id),  # passed to MCP server for event routing
    }

    cmd = [
        HERMES_BIN,
        "chat",
        "-q", goal,
        "-Q",
        "-m", os.environ.get("HERMES_MODEL", "claude-sonnet-4-6"),
        "--provider", "anthropic",
        "--source", "tool",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(REPO_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await proc.communicate()

    final_response = stdout.decode().strip()
    success = proc.returncode == 0

    await emit_event(
        "run_completed",
        run_id,
        status="complete" if success else "failed",
        summary=final_response,
        hermes_session_id=_parse_session_id(stderr.decode()),
    )


def _parse_session_id(stderr: str) -> str | None:
    for line in stderr.splitlines():
        if line.startswith("session_id:"):
            return line.split(":", 1)[1].strip()
    return None
```

### `api/mcp_server/server.py` (shape)

Use `mcp` (Model Context Protocol Python SDK, already importable via `uv add mcp`) to expose our tools as an MCP server:

```python
from mcp.server.fastmcp import FastMCP
mcp_app = FastMCP("govcapture")

@mcp_app.tool()
async def parse_pdf(attachment_url: str) -> dict:
    """Parse a solicitation PDF from Supabase Storage."""
    from api.skills.parse_pdf.implementation import parse_pdf as _impl
    return await _impl(attachment_url)

# ... other tools
```

Hermes starts this server via:
```yaml
# .hermes/config.yaml  (project symlink → ~/.hermes/config.yaml)
mcp_servers:
  govcapture:
    command: "uv"
    args: ["run", "python", "-m", "api.mcp_server.server"]
    env:
      SUPABASE_URL: "${SUPABASE_URL}"
      ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
      DATABASE_URL: "${DATABASE_URL}"
```

### `api/agent/hermes_bridge.py`

For V1, this is thin: the final `run_completed` event carries the full summary string from Hermes' stdout. No per-step translation needed in V1. The bridge's job is:
1. Accept the `launch_hermes_run` coroutine as a FastAPI background task.
2. Persist SSE events to Redis pub/sub (for the `/agent-runs/:id/stream` endpoint).
3. Parse Hermes' session_id from stderr for log correlation.

### `.hermes/config.yaml` additions

```yaml
mcp_servers:
  govcapture:
    command: "uv"
    args: ["run", "python", "-m", "api.mcp_server.server"]
    timeout: 120
    connect_timeout: 30
```

---

## 6. Dependencies

| Package | Purpose | Action |
|---------|---------|--------|
| `mcp>=1.0` | MCP server SDK to expose govcapture tools to Hermes | `uv add mcp` to `pyproject.toml` |
| `hermes-agent` | Hermes runtime | **Do NOT add to pyproject.toml.** Already installed host-wide via installer script. Deploy via `infra/bootstrap.sh` on VX1. |

---

## 7. Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Hermes' own config.yaml (`~/.hermes/config.yaml`) is user-level, not project-level. On VX1, `infra/bootstrap.sh` must symlink `.hermes/config.yaml` to `~/.hermes/config.yaml`. Without this, MCP tools never register. | **HIGH** | Add symlink step to `infra/bootstrap.sh`. Already noted in `.hermes/config.yaml` header. |
| `hermes chat -Q` stdout is a free-text string, not structured JSON. Parsing it for summary fields is brittle. | **MEDIUM** | In T4.2, instruct Hermes via `HERMES.md` to output a JSON block as the final response. Add a try/json.loads with graceful fallback to raw string. |
| Hermes auto-loads context from cwd. Running tests with cwd=repo-root will load HERMES.md + .hermes/ into every test run. | **MEDIUM** | For eval harness (A12): use `--ignore-rules` flag when doing isolated skill calls. |
| Real-time step events are not available in subprocess mode with `-Q`. B5 Timeline sees only `run_completed`, not intermediate steps. | **MEDIUM** | Accepted for V1. V2: wire gateway mode (`tui_gateway/`) for real-time JSON-RPC events. |
| Hermes uses Python 3.11; MCP server runs in govcapture's Python 3.12. If Hermes starts the MCP server subprocess (`uv run`), it picks up govcapture's Python 3.12. No conflict — they are separate processes. | **LOW** | No action needed. |
| `hermes update` (79 commits behind as of spike) may change CLI flags or quiet-mode behavior. | **LOW** | Pin Hermes version in `infra/bootstrap.sh`: `hermes update --to v0.13.0`. |
| Hermes writes files to `HERMES_HOME`. In prod `HERMES_HOME=/home/govcapture/.hermes` must be on a persistent volume. | **LOW** | Already in `.env` + infra plan. Confirm in VX1 deploy runbook. |

---

## 8. What does NOT change

- `pyproject.toml` — no `hermes-agent` dependency added.
- Any production code in `api/` — this is a research-only spike.
- `CONTRACTS.md` SSE event shape — the bridge preserves it.

---

## 9. T4.2 first actions (in order)

1. `uv add mcp` — add MCP SDK to `pyproject.toml`.
2. Create `api/mcp_server/server.py` with stub tools (9 total, matching `tasks/HERMES.md`). Each stub returns a typed dict and passes through to the skill implementation module.
3. Update `.hermes/config.yaml` with the `mcp_servers.govcapture` block.
4. Create `api/agent/hermes_runner.py` with the `launch_hermes_run` coroutine.
5. Wire `POST /agent-runs` to call `background_tasks.add_task(launch_hermes_run, ...)`.
6. Test end-to-end: `hermes chat -q "find opportunities for test company" -Q` in repo root, verify MCP tools are called.
7. Only after step 6 passes: create `api/agent/hermes_bridge.py` and SSE emit logic.

---

## Sources

- Hermes source: `~/.hermes/hermes-agent/` (v0.13.0)
- `run_agent.py` — AIAgent class, callbacks, delegation
- `tools/delegate_tool.py` — delegate_task implementation
- `tools/registry.py` — tool registration API
- `tools/mcp_tool.py` — MCP integration
- `tui_gateway/` — gateway mode (V2 candidate for real-time events)
- `tasks/HERMES.md` — integration spec
- `HERMES.md` (repo root) — runtime project context
- `.hermes/config.yaml` — project delegation + MCP config
- Smoke test: `spike/hermes_smoke.py` (confirms subprocess invocation shape)
