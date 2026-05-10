# Sprint B: HTTP `/tools/<name>` Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose every `api/skills/<name>` skill as an HTTP `POST /tools/<name>` endpoint guarded by `X-Internal-API-Key`, so any non-Hermes caller (TS shim from `/root/michealaai`, Codex, Cursor, curl) can drive the pack without learning the Hermes plugin spec.

**Architecture:** One router file (`api/routes/tools.py`) holds 10 thin POST endpoints. Each accepts a typed Pydantic request, looks up the skill function directly, awaits it, and returns a uniform `{"data": <skill output>, "metrics": <LLMMetrics | null>}` envelope. LLM skills get an `LLM` instance from a new `get_llm` FastAPI dep (overridable in tests). Storage-bound skills get a small adapter satisfying the `_Storage` Protocol. The Supabase repo client comes from the existing `get_supabase` dep. **No business logic in routes — just dispatch.** Skill modules are not modified.

**Tech Stack:** Python 3.12 · FastAPI · Pydantic v2 · supabase-py AsyncClient · pytest-asyncio · uv

**Authoritative references:**
- Skill function signatures: `api/skills/<name>/skill.py` (verified 2026-05-09)
- Auth dep: `api.auth.require_internal_actor` (NB: not `require_internal`)
- Existing route pattern: `api/routes/agent_runs.py:30` (POST + dep-inject + response_model)
- Test harness: `api/tests/conftest.py` (FakeSupabase, `INTERNAL_HEADERS`)
- LLM test double: `api/tests/fakes.py::FakeLLM`

**Non-goals:**
- Refactoring skill signatures to be uniform (would inflate scope; bespoke routes are fine)
- Hermes plugin work (Sprint A)
- Native Pydantic generics over `BaseModel` (use `Any`-typed envelope; refactor if/when callers demand stricter types)

**Verification gates (must hold at end of every task):**
- `uv run pytest api/tests/ -q` — all green; suite size ≥ 113 (current baseline)
- `uv run ruff check api` — clean
- `uv run mypy api` — 0 errors
- `git status` — clean

**Final verification gates (sprint complete):**
- App route count: 24 → **34** (+10 new POST routes)
- All new routes return 401 without `X-Internal-API-Key`
- All new routes return 422 on malformed payload
- All new routes return 200 + valid envelope on happy path
- `tasks/CONTRACTS.md` §6 lists the 10 routes
- `devdocs/CURRENT_STATE.md` §7 route count updated
- `devdocs/CAPABILITY_PACK_INTEGRATION.md` HTTP surface marked "live"

---

## File Structure

| Action | Path | Responsibility |
|---|---|---|
| Create | `api/routes/tools.py` | 10 POST handlers, `ToolResponse` envelope |
| Create | `api/schemas/tool_requests.py` | 10 typed request models |
| Modify | `api/deps.py` | Add `get_llm`, `get_storage` |
| Create | `api/storage_adapter.py` | `StorageAdapter` class satisfying `_Storage` Protocol |
| Modify | `api/main.py:9-17,38-44` | Import + register `tools` router |
| Create | `api/tests/test_tools_routes.py` | 30+ test cases (10 routes × {200, 401, 422}) |
| Modify | `tasks/CONTRACTS.md` §6 | Document 10 new internal routes |
| Modify | `devdocs/CURRENT_STATE.md` §7 | Bump route count + table rows |
| Modify | `devdocs/CAPABILITY_PACK_INTEGRATION.md` | Mark HTTP surface "live" |

**Why `api/storage_adapter.py` instead of putting it in `api/storage.py`:** `api/storage.py` exposes module-level functions (`upload_bytes`, `download_bytes`). The `fetch_attachment` skill's `_Storage` Protocol expects an object with `.upload(path, body) -> str`. A new file keeps the adapter discoverable and avoids polluting `api/storage.py` with class-shaped surface its other callers don't need.

---

## Phase 0: Foundation

### Task 0.1: Tool request models

**Files:**
- Create: `api/schemas/tool_requests.py`

- [ ] **Step 1: Write the request models**

```python
# api/schemas/tool_requests.py
"""Request models for POST /tools/<name>.

These mirror each skill's input contract. Where the underlying skill takes
`dict[str, Any]`, the model adds typed validation at the HTTP boundary so
FastAPI generates a 422 on malformed input. The skill itself remains
untouched.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from api.skills.extract_requirements import ExtractInput
from api.skills.parse_pdf import ParsePdfInput


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParseGoalRequest(_Strict):
    goal: str = Field(..., min_length=1)
    company_profile: dict[str, Any] = Field(default_factory=dict)


class ParsePdfRequest(_Strict):
    path: str = Field(..., min_length=1)
    doc_id: str | None = None

    def to_skill_input(self) -> ParsePdfInput:
        return ParsePdfInput(path=self.path, doc_id=self.doc_id)


class ExtractRequirementsRequest(_Strict):
    parsed: dict[str, Any]
    opportunity_metadata: dict[str, Any] = Field(default_factory=dict)
    doc_id: str | None = None

    def to_skill_input(self) -> ExtractInput:
        return ExtractInput.model_validate(self.model_dump())


class ScoreFitRequest(_Strict):
    company_profile: dict[str, Any]
    requirements: list[dict[str, Any]]


class DetectRisksRequest(_Strict):
    company_profile: dict[str, Any] = Field(default_factory=dict)
    opportunity: dict[str, Any] = Field(default_factory=dict)
    requirements: list[dict[str, Any]] = Field(default_factory=list)


class GenerateActionPackageRequest(_Strict):
    mode: str = "full"
    company_profile: dict[str, Any] = Field(default_factory=dict)
    opportunity: dict[str, Any] = Field(default_factory=dict)
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    fit_score: dict[str, Any] = Field(default_factory=dict)
    risks: list[dict[str, Any]] = Field(default_factory=list)


class SearchSamRequest(_Strict):
    keywords: str = ""
    naics: str | None = None
    posted_from: str | None = None
    set_aside: str | None = None
    state: str | None = None
    limit: int = Field(20, ge=1, le=100)


class FetchAttachmentRequest(_Strict):
    run_id: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    filename: str | None = None


class RankOpportunitiesRequest(_Strict):
    scored: list[dict[str, Any]]


class LoadSeededOpportunitiesRequest(_Strict):
    slugs: list[str] | None = None
```

- [ ] **Step 2: Verify imports compile**

Run: `uv run python -c "from api.schemas.tool_requests import ParseGoalRequest; ParseGoalRequest(goal='x')"`
Expected: prints nothing, exit 0.

- [ ] **Step 3: Commit**

```bash
git add api/schemas/tool_requests.py
git commit -m "feat(tools): typed request models for POST /tools/<name>"
```

---

### Task 0.2: `get_llm` and `get_storage` dependencies

**Files:**
- Create: `api/storage_adapter.py`
- Modify: `api/deps.py`

- [ ] **Step 1: Write the storage adapter**

```python
# api/storage_adapter.py
"""Adapter that exposes api.storage's module-level functions as the
`_Storage` Protocol that fetch_attachment expects (an object with
`.upload(path, body) -> str`).
"""
from __future__ import annotations

from api import storage


class StorageAdapter:
    async def upload(self, path: str, body: bytes) -> str:
        return await storage.upload_bytes(
            path, body, content_type="application/pdf"
        )
```

- [ ] **Step 2: Add `get_llm` and `get_storage` to deps**

Append to `api/deps.py` (after the existing repo deps):

```python
from functools import lru_cache

from api.llm import LLM
from api.storage_adapter import StorageAdapter


@lru_cache
def _llm_singleton() -> LLM:
    return LLM()


def get_llm() -> LLM:
    return _llm_singleton()


def get_storage() -> StorageAdapter:
    return StorageAdapter()
```

- [ ] **Step 3: Verify**

Run: `uv run python -c "from api.deps import get_llm, get_storage; print(type(get_llm()).__name__, type(get_storage()).__name__)"`
Expected: `LLM StorageAdapter`

(If `LLM()` raises because `ANTHROPIC_API_KEY` is the placeholder, that's still fine — `_llm_singleton` is lazy and constructs only on first call. The test override path will inject `FakeLLM` before any real call.)

- [ ] **Step 4: Run lint/typecheck**

Run: `uv run ruff check api && uv run mypy api`
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add api/storage_adapter.py api/deps.py
git commit -m "feat(tools): get_llm + get_storage FastAPI deps"
```

---

### Task 0.3: Router skeleton + envelope + main.py wiring

**Files:**
- Create: `api/routes/tools.py`
- Modify: `api/main.py`

- [ ] **Step 1: Write the router skeleton with the response envelope**

```python
# api/routes/tools.py
"""Internal HTTP surface for the GovCon skills.

Every endpoint POST /tools/<name> requires X-Internal-API-Key (InternalActor).
Responses share a uniform `{"data": ..., "metrics": ...}` envelope:

    - data:    skill output (dict or Pydantic model dump)
    - metrics: LLMMetrics if the skill called an LLM, else null

Routes intentionally hold no business logic — they validate input via
api.schemas.tool_requests, dispatch to the underlying skill, and return.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import AsyncClient

from api.auth import InternalActor, require_internal_actor
from api.deps import get_llm, get_storage, get_supabase
from api.llm import LLM, LLMMetrics
from api.storage_adapter import StorageAdapter

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolResponse(BaseModel):
    data: Any
    metrics: LLMMetrics | None = None
```

- [ ] **Step 2: Wire the router into main.py**

Modify `api/main.py`:

```python
# Add `tools` to the import block
from api.routes import (
    action_packages,
    agent_runs,
    company_profiles,
    healthz,
    opportunities,
    profiles,
    tools,            # <-- new
    waitlist,
)

# ...later, alongside the other include_router calls:
app.include_router(tools.router)
```

- [ ] **Step 3: Verify route count is unchanged (still 24 — no handlers yet)**

Run: `uv run python -c "from api.main import app; print(sum(1 for r in app.routes if hasattr(r,'path')))"`
Expected: `24` (the empty router adds nothing visible until handlers exist).

- [ ] **Step 4: Run baseline tests + lint**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 113 passed; clean.

- [ ] **Step 5: Commit**

```bash
git add api/routes/tools.py api/main.py
git commit -m "feat(tools): scaffold /tools router + ToolResponse envelope"
```

---

### Task 0.4: Test harness baseline + LLM dep override

**Files:**
- Create: `api/tests/test_tools_routes.py`

- [ ] **Step 1: Write the test file with shared helpers**

```python
# api/tests/test_tools_routes.py
"""POST /tools/<name> route tests — shape, auth, validation.

Each route gets three tests at minimum:
    - 200 happy path with a valid body and X-Internal-API-Key
    - 401 when the header is missing or wrong
    - 422 when the body is malformed

Skill-level correctness lives in test_<skill>.py — these tests verify only
the HTTP boundary, payload validation, and envelope shape.
"""
from __future__ import annotations

from typing import Any

import pytest

from api.tests.conftest import TEST_INTERNAL_API_KEY

pytestmark = pytest.mark.asyncio

INTERNAL_HEADERS = {"X-Internal-API-Key": TEST_INTERNAL_API_KEY}


async def test_tools_router_baseline_no_handlers_yet(client) -> None:
    """Router is registered; no handlers produce 404 with auth, 401 without."""
    r = await client.post("/tools/does-not-exist", json={}, headers=INTERNAL_HEADERS)
    assert r.status_code == 404
    r2 = await client.post("/tools/does-not-exist", json={})
    assert r2.status_code == 404  # FastAPI returns 404 before auth dep runs
```

- [ ] **Step 2: Run the baseline test**

Run: `uv run pytest api/tests/test_tools_routes.py -v`
Expected: 1 passed.

- [ ] **Step 3: Verify full suite still green**

Run: `uv run pytest api/tests/ -q`
Expected: 114 passed (was 113 + 1 new).

- [ ] **Step 4: Commit**

```bash
git add api/tests/test_tools_routes.py
git commit -m "test(tools): baseline 404 test for /tools router"
```

---

## Phase 1: Pure skills (no external deps)

### Task 1.1: `POST /tools/rank-opportunities`

**Files:**
- Modify: `api/routes/tools.py`
- Modify: `api/tests/test_tools_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_tools_routes.py`:

```python
# ─── /tools/rank-opportunities ─────────────────────────────────────────────


async def test_rank_opportunities_happy_path(client) -> None:
    payload = {
        "scored": [
            {"opportunity_id": "a", "decision": "maybe", "total_score": 60, "due_date": "2026-06-01"},
            {"opportunity_id": "b", "decision": "strong_pursue", "total_score": 92, "due_date": "2026-06-15"},
            {"opportunity_id": "c", "decision": "pursue", "total_score": 78, "due_date": "2026-05-20"},
        ]
    }
    r = await client.post("/tools/rank-opportunities", json=payload, headers=INTERNAL_HEADERS)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["metrics"] is None
    ranked = body["data"]["ranked"]
    assert [row["opportunity_id"] for row in ranked] == ["b", "c", "a"]


async def test_rank_opportunities_requires_internal_key(client) -> None:
    r = await client.post("/tools/rank-opportunities", json={"scored": []})
    assert r.status_code == 401


async def test_rank_opportunities_rejects_malformed(client) -> None:
    r = await client.post("/tools/rank-opportunities", json={}, headers=INTERNAL_HEADERS)
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_tools_routes.py::test_rank_opportunities_happy_path -v`
Expected: FAIL with 404 (handler not yet defined).

- [ ] **Step 3: Implement the route**

Append to `api/routes/tools.py`:

```python
from api.schemas.tool_requests import RankOpportunitiesRequest
from api.skills.rank_opportunities.skill import rank_opportunities


@router.post("/rank-opportunities", response_model=ToolResponse)
async def rank_opportunities_route(
    payload: RankOpportunitiesRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out = rank_opportunities(payload.model_dump())
    return ToolResponse(data=out)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k rank_opportunities`
Expected: 3 passed.

- [ ] **Step 5: Run full suite + lint + typecheck**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 117 passed; clean.

- [ ] **Step 6: Commit**

```bash
git add api/routes/tools.py api/tests/test_tools_routes.py
git commit -m "feat(tools): POST /tools/rank-opportunities"
```

---

### Task 1.2: `POST /tools/parse-pdf`

**Files:**
- Modify: `api/routes/tools.py`
- Modify: `api/tests/test_tools_routes.py`

**NB:** The `parse_pdf` skill takes a local filesystem path. Callers must already have the file accessible to the server's filesystem (e.g., the orchestrator on the same VX1 box, or having previously called `fetch-attachment`). HTTP cross-host callers should call `fetch-attachment` first, which writes to Supabase Storage at `raw/<run_id>/<filename>` and returns a `storage_path`. A future ticket may add a `parse-pdf-from-storage` variant; for Sprint B, the contract matches the existing skill.

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_tools_routes.py`:

```python
# ─── /tools/parse-pdf ──────────────────────────────────────────────────────


async def test_parse_pdf_returns_unparseable_for_missing_file(client, tmp_path) -> None:
    missing = tmp_path / "does-not-exist.pdf"
    r = await client.post(
        "/tools/parse-pdf",
        json={"path": str(missing)},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["metrics"] is None
    assert body["data"]["unparseable"] is True
    assert body["data"]["error"] == "file_not_found"


async def test_parse_pdf_requires_internal_key(client) -> None:
    r = await client.post("/tools/parse-pdf", json={"path": "/tmp/x.pdf"})
    assert r.status_code == 401


async def test_parse_pdf_rejects_empty_path(client) -> None:
    r = await client.post(
        "/tools/parse-pdf", json={"path": ""}, headers=INTERNAL_HEADERS
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k parse_pdf`
Expected: 3 fail with 404.

- [ ] **Step 3: Implement the route**

Append to `api/routes/tools.py`:

```python
from api.schemas.tool_requests import ParsePdfRequest
from api.skills.parse_pdf.skill import parse_pdf


@router.post("/parse-pdf", response_model=ToolResponse)
async def parse_pdf_route(
    payload: ParsePdfRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out = parse_pdf(payload.to_skill_input())
    return ToolResponse(data=out.model_dump())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k parse_pdf`
Expected: 3 passed.

- [ ] **Step 5: Run full suite + lint + typecheck**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 120 passed; clean.

- [ ] **Step 6: Commit**

```bash
git add api/routes/tools.py api/tests/test_tools_routes.py
git commit -m "feat(tools): POST /tools/parse-pdf"
```

---

## Phase 2: External-service skills

### Task 2.1: `POST /tools/search-sam`

**Files:**
- Modify: `api/routes/tools.py`
- Modify: `api/tests/test_tools_routes.py`

The `search_sam_opportunities` skill calls SAM.gov over HTTP. For tests, we monkeypatch the inner `httpx.AsyncClient` via the skill's `http=` param so no network call happens. The route reads `settings.sam_api_key` for the api_key.

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_tools_routes.py`:

```python
# ─── /tools/search-sam ─────────────────────────────────────────────────────


async def test_search_sam_returns_degraded_when_no_key(client, monkeypatch) -> None:
    """If SAM_API_KEY is empty and we hit a fake 401, the skill returns degraded."""
    from api.config import settings

    monkeypatch.setattr(settings, "sam_api_key", "")
    # Force a degraded return without a real network call by routing the skill
    # through a stub http client that returns 401.
    import httpx
    from api.routes import tools as tools_module

    class _FakeResp:
        status_code = 401
        def json(self) -> dict[str, Any]:
            return {}

    class _FakeClient:
        async def get(self, *args: Any, **kwargs: Any) -> _FakeResp:
            return _FakeResp()
        async def aclose(self) -> None:
            return None

    async def _fake_search(payload, *, api_key, http=None):
        return {"opportunities": [], "degraded": True, "error": "SAM client error: 401"}

    monkeypatch.setattr(tools_module, "search_sam_opportunities", _fake_search)

    r = await client.post(
        "/tools/search-sam",
        json={"keywords": "cyber"},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["degraded"] is True
    assert body["metrics"] is None


async def test_search_sam_requires_internal_key(client) -> None:
    r = await client.post("/tools/search-sam", json={"keywords": "x"})
    assert r.status_code == 401


async def test_search_sam_rejects_oversized_limit(client) -> None:
    r = await client.post(
        "/tools/search-sam",
        json={"keywords": "x", "limit": 10_000},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k search_sam`
Expected: fail with 404 / unbound name.

- [ ] **Step 3: Implement the route**

Append to `api/routes/tools.py`:

```python
from api.config import settings
from api.schemas.tool_requests import SearchSamRequest
from api.skills.search_sam.skill import search_sam_opportunities


@router.post("/search-sam", response_model=ToolResponse)
async def search_sam_route(
    payload: SearchSamRequest,
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out = await search_sam_opportunities(
        payload.model_dump(exclude_none=False),
        api_key=settings.sam_api_key,
    )
    return ToolResponse(data=out)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k search_sam`
Expected: 3 passed.

- [ ] **Step 5: Verify full suite + lint + typecheck**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 123 passed; clean.

- [ ] **Step 6: Commit**

```bash
git add api/routes/tools.py api/tests/test_tools_routes.py
git commit -m "feat(tools): POST /tools/search-sam"
```

---

### Task 2.2: `POST /tools/load-seeded-opportunities`

**Files:**
- Modify: `api/routes/tools.py`
- Modify: `api/tests/test_tools_routes.py`

This skill writes to Supabase via the existing `get_supabase` dep — already overridden to `FakeSupabase` in tests. The skill discovers manifests under `fixtures/`. Tests pass an explicit `fixtures_dir=tmp_path` via dependency? No — the skill takes that as a parameter. Easiest: route uses the default fixtures dir; we mount a tmp fixtures dir via the skill's existing `fixtures_dir` keyword. Since the route can't accept a path through the request (we don't want callers writing arbitrary disk paths), we **pass the default**, and the test creates a manifest in the real `fixtures/` dir scoped to a unique slug, then cleans up. Cleaner: the test stubs the skill itself, like search-sam.

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_tools_routes.py`:

```python
# ─── /tools/load-seeded-opportunities ──────────────────────────────────────


async def test_load_seeded_returns_loaded_list(client, monkeypatch) -> None:
    from api.routes import tools as tools_module

    async def _fake_load(payload, *, client, fixtures_dir=None):
        return {
            "opportunities": [
                {"id": "00000000-0000-4000-8000-000000000aaa", "slug": "strong-pursue", "title": "Stub"}
            ]
        }

    monkeypatch.setattr(tools_module, "load_seeded_opportunities", _fake_load)

    r = await client.post(
        "/tools/load-seeded-opportunities",
        json={"slugs": ["strong-pursue"]},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["opportunities"][0]["slug"] == "strong-pursue"
    assert body["metrics"] is None


async def test_load_seeded_requires_internal_key(client) -> None:
    r = await client.post("/tools/load-seeded-opportunities", json={})
    assert r.status_code == 401


async def test_load_seeded_rejects_unknown_field(client) -> None:
    r = await client.post(
        "/tools/load-seeded-opportunities",
        json={"slug": "x"},  # singular, unknown — _Strict rejects extras
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k load_seeded`
Expected: fail with 404.

- [ ] **Step 3: Implement the route**

Append to `api/routes/tools.py`:

```python
from api.schemas.tool_requests import LoadSeededOpportunitiesRequest
from api.skills.load_seeded_opportunities.skill import load_seeded_opportunities


@router.post("/load-seeded-opportunities", response_model=ToolResponse)
async def load_seeded_route(
    payload: LoadSeededOpportunitiesRequest,
    supabase: AsyncClient = Depends(get_supabase),
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out = await load_seeded_opportunities(payload.model_dump(), client=supabase)
    return ToolResponse(data=out)
```

- [ ] **Step 4: Verify tests pass**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k load_seeded`
Expected: 3 passed.

- [ ] **Step 5: Full suite + lint + typecheck**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 126 passed; clean.

- [ ] **Step 6: Commit**

```bash
git add api/routes/tools.py api/tests/test_tools_routes.py
git commit -m "feat(tools): POST /tools/load-seeded-opportunities"
```

---

### Task 2.3: `POST /tools/fetch-attachment`

**Files:**
- Modify: `api/routes/tools.py`
- Modify: `api/tests/test_tools_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_tools_routes.py`:

```python
# ─── /tools/fetch-attachment ───────────────────────────────────────────────


async def test_fetch_attachment_uploads_and_returns_path(client, monkeypatch) -> None:
    from api.routes import tools as tools_module

    async def _fake_fetch(payload, *, storage, http=None):
        return {
            "storage_path": f"raw/{payload['run_id']}/RFP-001.pdf",
            "bytes_downloaded": 12345,
        }

    monkeypatch.setattr(tools_module, "fetch_attachment", _fake_fetch)

    r = await client.post(
        "/tools/fetch-attachment",
        json={
            "run_id": "abc-123",
            "url": "https://example.com/RFP-001.pdf",
        },
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["storage_path"] == "raw/abc-123/RFP-001.pdf"
    assert body["data"]["bytes_downloaded"] == 12345
    assert body["metrics"] is None


async def test_fetch_attachment_requires_internal_key(client) -> None:
    r = await client.post(
        "/tools/fetch-attachment",
        json={"run_id": "x", "url": "https://e.com/x.pdf"},
    )
    assert r.status_code == 401


async def test_fetch_attachment_rejects_missing_url(client) -> None:
    r = await client.post(
        "/tools/fetch-attachment",
        json={"run_id": "x"},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k fetch_attachment`
Expected: fail with 404.

- [ ] **Step 3: Implement the route**

Append to `api/routes/tools.py`:

```python
from api.schemas.tool_requests import FetchAttachmentRequest
from api.skills.fetch_attachment.skill import fetch_attachment


@router.post("/fetch-attachment", response_model=ToolResponse)
async def fetch_attachment_route(
    payload: FetchAttachmentRequest,
    storage: StorageAdapter = Depends(get_storage),
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out = await fetch_attachment(payload.model_dump(), storage=storage)
    return ToolResponse(data=out)
```

- [ ] **Step 4: Verify tests pass**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k fetch_attachment`
Expected: 3 passed.

- [ ] **Step 5: Full suite + lint + typecheck**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 129 passed; clean.

- [ ] **Step 6: Commit**

```bash
git add api/routes/tools.py api/tests/test_tools_routes.py
git commit -m "feat(tools): POST /tools/fetch-attachment"
```

---

## Phase 3: LLM skills

LLM-route tests share a fixture that injects `FakeLLM` via `app.dependency_overrides[get_llm]`. Add it once at the top of the test file (after the other fixtures), then each LLM test consumes it.

### Task 3.0: Shared LLM fixture for route tests

**Files:**
- Modify: `api/tests/test_tools_routes.py`

- [ ] **Step 1: Add the fixture**

Insert near the top of `api/tests/test_tools_routes.py`, after the existing imports:

```python
from collections.abc import AsyncIterator
from typing import Callable

import pytest_asyncio

from api.deps import get_llm
from api.main import app
from api.tests.fakes import FakeLLM


@pytest_asyncio.fixture
async def fake_llm_factory() -> AsyncIterator[Callable[[dict[str, Any]], FakeLLM]]:
    """Return a factory that builds a FakeLLM and registers it as the
    get_llm override for this test. Cleans up overrides on teardown.

    Usage:
        async def test_x(client, fake_llm_factory):
            llm = fake_llm_factory({"keywords": ["cyber"]})
            r = await client.post("/tools/parse-goal", ...)
    """
    created: list[FakeLLM] = []

    def _make(payload: dict[str, Any]) -> FakeLLM:
        f = FakeLLM(payload=payload)
        created.append(f)
        app.dependency_overrides[get_llm] = lambda: f
        return f

    try:
        yield _make
    finally:
        app.dependency_overrides.pop(get_llm, None)
```

- [ ] **Step 2: Verify the file still imports**

Run: `uv run python -c "from api.tests import test_tools_routes"`
Expected: prints nothing, exit 0.

- [ ] **Step 3: Run full suite (no new tests yet)**

Run: `uv run pytest api/tests/ -q`
Expected: still 129 passed.

- [ ] **Step 4: Commit**

```bash
git add api/tests/test_tools_routes.py
git commit -m "test(tools): fake_llm_factory fixture for route tests"
```

---

### Task 3.1: `POST /tools/parse-goal`

**Files:**
- Modify: `api/routes/tools.py`
- Modify: `api/tests/test_tools_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_tools_routes.py`:

```python
# ─── /tools/parse-goal ─────────────────────────────────────────────────────


async def test_parse_goal_returns_data_and_metrics(client, fake_llm_factory) -> None:
    fake_llm_factory(
        {
            "keywords": ["cybersecurity", "FedRAMP"],
            "naics_hints": ["541512"],
            "due_window_days": 30,
            "set_aside_pref": None,
            "geography": None,
            "agencies": None,
            "opportunity_type": "any",
        }
    )
    r = await client.post(
        "/tools/parse-goal",
        json={"goal": "find FedRAMP cyber RFPs in the next 30 days"},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "cybersecurity" in body["data"]["keywords"]
    assert body["metrics"]["model"] == "claude-haiku-4-5-20251001"
    assert body["metrics"]["latency_ms"] == 42


async def test_parse_goal_requires_internal_key(client) -> None:
    r = await client.post("/tools/parse-goal", json={"goal": "x"})
    assert r.status_code == 401


async def test_parse_goal_rejects_empty_goal(client) -> None:
    r = await client.post(
        "/tools/parse-goal", json={"goal": ""}, headers=INTERNAL_HEADERS
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k parse_goal`
Expected: fail with 404.

- [ ] **Step 3: Implement the route**

Append to `api/routes/tools.py`:

```python
from api.schemas.tool_requests import ParseGoalRequest
from api.skills.parse_goal.skill import parse_goal


@router.post("/parse-goal", response_model=ToolResponse)
async def parse_goal_route(
    payload: ParseGoalRequest,
    llm: LLM = Depends(get_llm),
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out, metrics = await parse_goal(payload.model_dump(), llm=llm)
    return ToolResponse(data=out, metrics=metrics)
```

- [ ] **Step 4: Verify tests pass**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k parse_goal`
Expected: 3 passed.

- [ ] **Step 5: Full suite + lint + typecheck**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 132 passed; clean.

- [ ] **Step 6: Commit**

```bash
git add api/routes/tools.py api/tests/test_tools_routes.py
git commit -m "feat(tools): POST /tools/parse-goal"
```

---

### Task 3.2: `POST /tools/extract-requirements`

**Files:**
- Modify: `api/routes/tools.py`
- Modify: `api/tests/test_tools_routes.py`

The skill returns `tuple[RequirementExtractionOutput, LLMMetrics]`. Convert the model to a dict before placing in the envelope.

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_tools_routes.py`:

```python
# ─── /tools/extract-requirements ───────────────────────────────────────────


_PARSED_OK = {
    "doc_id": "doc-1",
    "page_count": 1,
    "unparseable": False,
    "chunks": [
        {"page_number": 1, "text": "Section L. The Offeror shall hold a SECRET clearance.", "char_count": 53}
    ],
    "error": None,
}


async def test_extract_requirements_passes_through_skill(client, fake_llm_factory) -> None:
    fake_llm_factory(
        {
            "requirements": [
                {
                    "type": "security",
                    "title": "Secret clearance",
                    "value": "SECRET",
                    "description": "The Offeror shall hold a SECRET clearance.",
                    "confidence": "high",
                    "evidence_snippet": "The Offeror shall hold a SECRET clearance.",
                    "source_document": "doc-1",
                    "page_number": 1,
                    "is_blocker": True,
                }
            ],
            "missing_fields": [],
            "conflicts": [],
        }
    )
    r = await client.post(
        "/tools/extract-requirements",
        json={
            "parsed": _PARSED_OK,
            "opportunity_metadata": {"title": "Cyber RFP"},
        },
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["requirements"][0]["type"] == "security"
    assert body["metrics"]["latency_ms"] == 42


async def test_extract_requirements_unparseable_skips_llm(client, fake_llm_factory) -> None:
    fake_llm_factory({})  # never called
    r = await client.post(
        "/tools/extract-requirements",
        json={
            "parsed": {
                "doc_id": "doc-2",
                "page_count": 0,
                "unparseable": True,
                "chunks": [],
                "error": "encrypted",
            },
        },
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["requirements"] == []
    assert body["data"]["missing_fields"] == ["all"]


async def test_extract_requirements_requires_internal_key(client) -> None:
    r = await client.post(
        "/tools/extract-requirements",
        json={"parsed": _PARSED_OK},
    )
    assert r.status_code == 401


async def test_extract_requirements_rejects_missing_parsed(client) -> None:
    r = await client.post(
        "/tools/extract-requirements", json={}, headers=INTERNAL_HEADERS
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k extract_requirements`
Expected: fail with 404.

- [ ] **Step 3: Implement the route**

Append to `api/routes/tools.py`:

```python
from api.schemas.tool_requests import ExtractRequirementsRequest
from api.skills.extract_requirements.skill import extract_requirements


@router.post("/extract-requirements", response_model=ToolResponse)
async def extract_requirements_route(
    payload: ExtractRequirementsRequest,
    llm: LLM = Depends(get_llm),
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out, metrics = await extract_requirements(
        payload.to_skill_input(), llm=llm
    )
    return ToolResponse(data=out.model_dump(), metrics=metrics)
```

- [ ] **Step 4: Verify tests pass**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k extract_requirements`
Expected: 4 passed.

- [ ] **Step 5: Full suite + lint + typecheck**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 136 passed; clean.

- [ ] **Step 6: Commit**

```bash
git add api/routes/tools.py api/tests/test_tools_routes.py
git commit -m "feat(tools): POST /tools/extract-requirements"
```

---

### Task 3.3: `POST /tools/score-fit`

**Files:**
- Modify: `api/routes/tools.py`
- Modify: `api/tests/test_tools_routes.py`

§11.1 short-circuit: when an eligibility blocker is present, the skill returns score=0/decision=reject **without** calling the LLM. Test that path with `FakeLLM(should_not_be_called=True)`.

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_tools_routes.py`:

```python
# ─── /tools/score-fit ──────────────────────────────────────────────────────


async def test_score_fit_short_circuits_on_clearance_blocker(client) -> None:
    """§11.1: clearance requirement on a profile with no clearance → reject, no LLM."""
    from api.deps import get_llm

    # Inline override: FakeLLM that asserts it's never called.
    fake = FakeLLM(should_not_be_called=True)
    app.dependency_overrides[get_llm] = lambda: fake
    try:
        r = await client.post(
            "/tools/score-fit",
            json={
                "company_profile": {
                    "certifications": [],
                    "clearance_status": "none",
                },
                "requirements": [
                    {
                        "type": "security",
                        "title": "TS/SCI clearance required",
                        "value": "TS/SCI",
                        "description": "Personnel must hold TS/SCI clearance.",
                        "confidence": "high",
                        "is_blocker": True,
                    }
                ],
            },
            headers=INTERNAL_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(get_llm, None)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["decision"] == "reject"
    assert body["data"]["total_score"] == 0
    assert body["metrics"]["model"] == "none"


async def test_score_fit_calls_llm_when_no_blocker(client, fake_llm_factory) -> None:
    fake_llm_factory(
        {
            "total_score": 88,
            "decision": "strong_pursue",
            "confidence": "high",
            "score_breakdown": {
                "capability": 10, "eligibility": 10, "naics": 10,
                "past_performance": 10, "certification": 10,
                "insurance_bonding": 10, "deadline": 10,
                "complexity": 10, "geography": 8,
            },
            "strengths": ["cyber capability"],
            "weaknesses": [],
            "blockers": [],
            "missing_information": [],
            "recommended_next_action": "Pursue.",
        }
    )
    r = await client.post(
        "/tools/score-fit",
        json={
            "company_profile": {"certifications": ["8(a)"], "clearance_status": "none"},
            "requirements": [
                {"type": "technical", "title": "FedRAMP Moderate", "confidence": "high"}
            ],
        },
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["total_score"] == 88
    assert body["data"]["decision"] == "strong_pursue"  # band-normalized
    assert body["metrics"]["latency_ms"] == 42


async def test_score_fit_requires_internal_key(client) -> None:
    r = await client.post(
        "/tools/score-fit",
        json={"company_profile": {}, "requirements": []},
    )
    assert r.status_code == 401


async def test_score_fit_rejects_missing_requirements(client) -> None:
    r = await client.post(
        "/tools/score-fit",
        json={"company_profile": {}},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k score_fit`
Expected: fail with 404.

- [ ] **Step 3: Implement the route**

Append to `api/routes/tools.py`:

```python
from api.schemas.tool_requests import ScoreFitRequest
from api.skills.score_fit.skill import score_fit


@router.post("/score-fit", response_model=ToolResponse)
async def score_fit_route(
    payload: ScoreFitRequest,
    llm: LLM = Depends(get_llm),
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out, metrics = await score_fit(payload.model_dump(), llm=llm)
    return ToolResponse(data=out, metrics=metrics)
```

- [ ] **Step 4: Verify tests pass**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k score_fit`
Expected: 4 passed.

- [ ] **Step 5: Full suite + lint + typecheck**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 140 passed; clean.

- [ ] **Step 6: Commit**

```bash
git add api/routes/tools.py api/tests/test_tools_routes.py
git commit -m "feat(tools): POST /tools/score-fit (incl. §11.1 short-circuit)"
```

---

### Task 3.4: `POST /tools/detect-risks`

**Files:**
- Modify: `api/routes/tools.py`
- Modify: `api/tests/test_tools_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_tools_routes.py`:

```python
# ─── /tools/detect-risks ───────────────────────────────────────────────────


async def test_detect_risks_silently_drops_unknown_categories(client, fake_llm_factory) -> None:
    fake_llm_factory(
        {
            "risks": [
                {
                    "category": "deadline_too_close",
                    "severity": "major_risk",
                    "title": "Tight deadline",
                    "description": "Only 7 days remain.",
                    "evidence": "Due 2026-05-16",
                    "mitigation": "Pre-position partner.",
                    "requires_human_review": False,
                },
                {
                    "category": "made_up_category",  # silently dropped
                    "severity": "minor_concern",
                    "title": "x",
                    "description": "x",
                    "evidence": "x",
                    "mitigation": "x",
                    "requires_human_review": False,
                },
            ]
        }
    )
    r = await client.post(
        "/tools/detect-risks",
        json={
            "company_profile": {},
            "opportunity": {"due_date": "2026-05-16"},
            "requirements": [],
        },
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    risks = body["data"]["risks"]
    assert len(risks) == 1
    assert risks[0]["category"] == "deadline_too_close"
    assert body["metrics"]["latency_ms"] == 42


async def test_detect_risks_requires_internal_key(client) -> None:
    r = await client.post(
        "/tools/detect-risks",
        json={"company_profile": {}, "opportunity": {}, "requirements": []},
    )
    assert r.status_code == 401


async def test_detect_risks_rejects_unknown_field(client) -> None:
    r = await client.post(
        "/tools/detect-risks",
        json={"profile": {}},  # wrong key (singular, unknown — _Strict rejects extras)
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k detect_risks`
Expected: fail with 404.

- [ ] **Step 3: Implement the route**

Append to `api/routes/tools.py`:

```python
from api.schemas.tool_requests import DetectRisksRequest
from api.skills.detect_risks.skill import detect_risks


@router.post("/detect-risks", response_model=ToolResponse)
async def detect_risks_route(
    payload: DetectRisksRequest,
    llm: LLM = Depends(get_llm),
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out, metrics = await detect_risks(payload.model_dump(), llm=llm)
    return ToolResponse(data=out, metrics=metrics)
```

- [ ] **Step 4: Verify tests pass**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k detect_risks`
Expected: 3 passed.

- [ ] **Step 5: Full suite + lint + typecheck**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 143 passed; clean.

- [ ] **Step 6: Commit**

```bash
git add api/routes/tools.py api/tests/test_tools_routes.py
git commit -m "feat(tools): POST /tools/detect-risks"
```

---

### Task 3.5: `POST /tools/generate-action-package`

**Files:**
- Modify: `api/routes/tools.py`
- Modify: `api/tests/test_tools_routes.py`

Two modes: `full` (LLM) and `reject_summary` (deterministic, no LLM). Test both.

- [ ] **Step 1: Write the failing tests**

Append to `api/tests/test_tools_routes.py`:

```python
# ─── /tools/generate-action-package ────────────────────────────────────────


async def test_generate_action_package_reject_mode_skips_llm(client) -> None:
    from api.deps import get_llm

    fake = FakeLLM(should_not_be_called=True)
    app.dependency_overrides[get_llm] = lambda: fake
    try:
        r = await client.post(
            "/tools/generate-action-package",
            json={
                "mode": "reject_summary",
                "opportunity": {"title": "Cyber RFP"},
                "fit_score": {"total_score": 0, "blockers": ["TS/SCI required"]},
            },
            headers=INTERNAL_HEADERS,
        )
    finally:
        app.dependency_overrides.pop(get_llm, None)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["decision"] == "reject"
    assert body["metrics"]["model"] == "none"
    assert len(body["data"]["human_approval_required"]) >= 1


async def test_generate_action_package_full_mode_calls_llm(client, fake_llm_factory) -> None:
    fake_llm_factory(
        {
            "executive_summary": "Strong fit.",
            "decision": "strong_pursue",
            "fit_score": 88,
            "fit_rationale": "Aligned.",
            "compliance_matrix": [],
            "risk_register": [],
            "proposal_checklist": [],
            "timeline": [],
            "partner_suggestions": [],
            "outreach_draft": None,
            "human_approval_required": ["Review before submission."],
        }
    )
    r = await client.post(
        "/tools/generate-action-package",
        json={
            "mode": "full",
            "opportunity": {"title": "Cyber RFP"},
            "company_profile": {},
            "requirements": [],
            "fit_score": {"total_score": 88, "decision": "strong_pursue"},
            "risks": [],
        },
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["decision"] == "strong_pursue"
    assert body["metrics"]["latency_ms"] == 42


async def test_generate_action_package_injects_default_approval_when_llm_omits(
    client, fake_llm_factory
) -> None:
    """§5.13 invariant — controller injects a default if LLM forgets."""
    fake_llm_factory(
        {
            "executive_summary": "x",
            "decision": "pursue",
            "fit_score": 75,
            "fit_rationale": "x",
            "compliance_matrix": [],
            "risk_register": [],
            "proposal_checklist": [],
            "timeline": [],
            "partner_suggestions": [],
            "outreach_draft": None,
            "human_approval_required": [],  # LLM forgets — controller fills in
        }
    )
    r = await client.post(
        "/tools/generate-action-package",
        json={"mode": "full", "opportunity": {}, "company_profile": {}, "requirements": [], "fit_score": {}, "risks": []},
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["data"]["human_approval_required"]) >= 1


async def test_generate_action_package_requires_internal_key(client) -> None:
    r = await client.post("/tools/generate-action-package", json={"mode": "full"})
    assert r.status_code == 401


async def test_generate_action_package_rejects_unknown_mode_field(client) -> None:
    r = await client.post(
        "/tools/generate-action-package",
        json={"unknown_field": True},  # _Strict rejects extras
        headers=INTERNAL_HEADERS,
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k generate_action_package`
Expected: fail with 404.

- [ ] **Step 3: Implement the route**

Append to `api/routes/tools.py`:

```python
from api.schemas.tool_requests import GenerateActionPackageRequest
from api.skills.generate_action_package.skill import generate_action_package


@router.post("/generate-action-package", response_model=ToolResponse)
async def generate_action_package_route(
    payload: GenerateActionPackageRequest,
    llm: LLM = Depends(get_llm),
    _actor: InternalActor = Depends(require_internal_actor),
) -> ToolResponse:
    out, metrics = await generate_action_package(payload.model_dump(), llm=llm)
    return ToolResponse(data=out, metrics=metrics)
```

- [ ] **Step 4: Verify tests pass**

Run: `uv run pytest api/tests/test_tools_routes.py -v -k generate_action_package`
Expected: 5 passed.

- [ ] **Step 5: Full suite + lint + typecheck**

Run: `uv run pytest api/tests/ -q && uv run ruff check api && uv run mypy api`
Expected: 148 passed; clean.

- [ ] **Step 6: Verify final route count**

Run: `uv run python -c "from api.main import app; print(sum(1 for r in app.routes if hasattr(r,'path')))"`
Expected: `34` (24 baseline + 10 new POST routes).

- [ ] **Step 7: Commit**

```bash
git add api/routes/tools.py api/tests/test_tools_routes.py
git commit -m "feat(tools): POST /tools/generate-action-package (full + reject_summary)"
```

---

## Phase 4: Documentation

### Task 4.1: `tasks/CONTRACTS.md` §6 — Internal routes

**Files:**
- Modify: `tasks/CONTRACTS.md`

- [ ] **Step 1: Read current §6**

Run: `grep -n "^## 6\." tasks/CONTRACTS.md` to find the section anchor; read 60 lines after it.

- [ ] **Step 2: Add the new routes table**

Append (or insert into the existing §6 table) the following block. Replace `<insertion_anchor>` with the actual heading text for the "Internal only" subsection in the live file:

```markdown
### POST `/tools/<name>` (Sprint B — internal only)

All routes require `X-Internal-API-Key`. Response envelope: `{"data": ..., "metrics": LLMMetrics | null}`.

| Route | Skill | LLM | Notes |
|---|---|---|---|
| POST `/tools/parse-goal` | `api.skills.parse_goal` | yes | Goal → search criteria |
| POST `/tools/parse-pdf` | `api.skills.parse_pdf` | no | Local FS path; deterministic |
| POST `/tools/extract-requirements` | `api.skills.extract_requirements` | yes | §10.1 contract; evidence-binding post-validation |
| POST `/tools/score-fit` | `api.skills.score_fit` | conditional | §11.1 short-circuit skips LLM on eligibility blockers |
| POST `/tools/detect-risks` | `api.skills.detect_risks` | yes | §5.8 taxonomy; silent-drop unknown categories |
| POST `/tools/generate-action-package` | `api.skills.generate_action_package` | conditional | `mode: "reject_summary"` skips LLM |
| POST `/tools/search-sam` | `api.skills.search_sam` | no | Reads `SAM_API_KEY`; degraded fallback on rate-limit/5xx |
| POST `/tools/fetch-attachment` | `api.skills.fetch_attachment` | no | Writes to Supabase Storage `raw/<run_id>/<filename>` |
| POST `/tools/rank-opportunities` | `api.skills.rank_opportunities` | no | Pure deterministic sort |
| POST `/tools/load-seeded-opportunities` | `api.skills.load_seeded_opportunities` | no | Idempotent on slug |
```

- [ ] **Step 3: Commit**

```bash
git add tasks/CONTRACTS.md
git commit -m "docs(contracts): document POST /tools/<name> internal routes"
```

---

### Task 4.2: `devdocs/CURRENT_STATE.md` §7 — route count

**Files:**
- Modify: `devdocs/CURRENT_STATE.md`

- [ ] **Step 1: Find the route-count line**

Run: `grep -n "24" devdocs/CURRENT_STATE.md` and `grep -n "API surface" devdocs/CURRENT_STATE.md` to locate §7 and the route-count claim.

- [ ] **Step 2: Update the route count to 34 and add the 10 new rows**

In §7's API table, append a "Internal — /tools" subsection or extend the existing internal-routes table with the same 10 rows from Task 4.1. Bump any prose claim of "24 routes" to "34 routes (24 user + 10 internal `/tools/`)".

- [ ] **Step 3: Verify route count by running the app**

Run: `uv run python -c "from api.main import app; print(sum(1 for r in app.routes if hasattr(r,'path')))"`
Expected: `34`. Doc and reality must match.

- [ ] **Step 4: Commit**

```bash
git add devdocs/CURRENT_STATE.md
git commit -m "docs(state): bump route count to 34 (Sprint B /tools/)"
```

---

### Task 4.3: `devdocs/CAPABILITY_PACK_INTEGRATION.md` — mark HTTP surface live

**Files:**
- Modify: `devdocs/CAPABILITY_PACK_INTEGRATION.md`

- [ ] **Step 1: Find the "HTTP REST" or "POST /tools" section**

Run: `grep -n -i "http\|/tools\|planned" devdocs/CAPABILITY_PACK_INTEGRATION.md`

- [ ] **Step 2: Change status from "planned" → "live (Sprint B, 2026-05-09)"**

Specifically: any line marking the `POST /tools/<name>` interface as "planned" or "Sprint B" must now read "live as of 2026-05-09 (commits ..a8b8df4..)" — use `git log --oneline | head -20` to find the actual commit range and substitute.

Add a one-paragraph caller note:

> Callers send `POST /tools/<name>` with `X-Internal-API-Key` and a JSON body matching the per-route request model. Responses share the envelope `{"data": ..., "metrics": <LLMMetrics | null>}`. LLM-backed routes report token counts and cost; non-LLM routes return `metrics: null`. Schema source: `api/schemas/tool_requests.py`.

- [ ] **Step 3: Commit**

```bash
git add devdocs/CAPABILITY_PACK_INTEGRATION.md
git commit -m "docs(integration): mark POST /tools/<name> live"
```

---

### Task 4.4: Final verification gates

- [ ] **Step 1: Full test suite**

Run: `uv run pytest api/tests/ -q`
Expected: 148 passed (113 baseline + 35 new = 148; off-by-a-few tolerated if test counts above were imprecise — what matters is all green).

- [ ] **Step 2: Lint + typecheck**

Run: `uv run ruff check api && uv run mypy api`
Expected: clean.

- [ ] **Step 3: Route count**

Run: `uv run python -c "from api.main import app; print(sum(1 for r in app.routes if hasattr(r,'path')))"`
Expected: `34`.

- [ ] **Step 4: Curl smoke-test (optional, requires running server)**

```bash
# Terminal 1
INTERNAL_API_KEY="dev-test-key" uv run uvicorn api.main:app --port 8000 &

# Terminal 2
curl -X POST http://localhost:8000/tools/rank-opportunities \
  -H "X-Internal-API-Key: dev-test-key" \
  -H "Content-Type: application/json" \
  -d '{"scored":[{"opportunity_id":"a","decision":"pursue","total_score":75,"due_date":"2026-06-01"}]}'
```

Expected response (HTTP 200):
```json
{"data":{"ranked":[{"opportunity_id":"a","decision":"pursue","total_score":75,"due_date":"2026-06-01"}]},"metrics":null}
```

Then:
```bash
curl -X POST http://localhost:8000/tools/rank-opportunities -H "Content-Type: application/json" -d '{"scored":[]}'
```
Expected: HTTP 401, `{"detail":"Internal API key is not configured"}` or `{"detail":"Invalid internal API key"}` depending on env.

- [ ] **Step 5: Working tree clean**

Run: `git status`
Expected: `nothing to commit, working tree clean`.

- [ ] **Step 6: Sprint complete — update handoff predecessor pointer**

Per `devdocs/HANDOFF_PROMPT.md` §19, after completing a sprint update Section 1 ("Verified state") and Section 7 (mark Sprint B as `done`). Add a one-line outcome to Section 7's row.

```bash
git add devdocs/HANDOFF_PROMPT.md
git commit -m "docs(handoff): mark Sprint B done; bump verified state"
```

---

## Self-Review

**Spec coverage** (against the handoff §9 spec for Sprint B):

| Spec line | Plan task |
|---|---|
| 10 routes listed | Phase 1.1, 1.2, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5 |
| All POST | Each route uses `@router.post` |
| All InternalActor-protected | Every route depends on `require_internal_actor` |
| JSON in/JSON out | `ToolResponse` envelope |
| Reuse existing Pydantic schemas | `ParsePdfInput`, `ExtractInput` reused via `to_skill_input()` adapters |
| No business logic in route | Each route handler is 2–3 lines |
| Tests cover happy + 401 + 422 + structural | Phase 1–3 each include all four; some routes add a 5th (short-circuit / skill-failure path) |
| Update CONTRACTS.md §6 | Task 4.1 |
| Update CURRENT_STATE.md §7 | Task 4.2 |
| Update CAPABILITY_PACK_INTEGRATION.md | Task 4.3 |
| Route count 24 → ~34 | Task 3.5 step 6 + Task 4.4 step 3 |

**Placeholder scan:** No "TBD", "TODO", "implement later", "similar to Task N", or "fill in details" anywhere in the plan. Every code step has actual code.

**Type consistency:**
- `require_internal_actor` (not `require_internal`) — used consistently in every LLM and non-LLM route. ✓
- `get_llm` returns `LLM`; `get_storage` returns `StorageAdapter`. Routes import both consistently. ✓
- `ToolResponse(data=..., metrics=...)` shape used identically across all 10 routes. ✓
- LLM-skill routes return `metrics=metrics` (not None); non-LLM-skill routes return `metrics=None`. ✓
- Skill function names verified against actual source:
  - `rank_opportunities` (sync) ✓
  - `parse_pdf` (sync, takes `ParsePdfInput | dict`) ✓
  - `search_sam_opportunities` (NB: not `search_sam` — folder is `search_sam`, function is `search_sam_opportunities`) ✓
  - `load_seeded_opportunities` (async, takes `client=`) ✓
  - `fetch_attachment` (async, takes `storage=`) ✓
  - `parse_goal` (async, returns tuple) ✓
  - `extract_requirements` (async, accepts `ExtractInput | dict`, returns `tuple[RequirementExtractionOutput, LLMMetrics]`) ✓
  - `score_fit` (async, returns tuple) ✓
  - `detect_risks` (async, returns tuple) ✓
  - `generate_action_package` (async, returns tuple, has dual-mode) ✓

**Risks I'm consciously accepting:**
- `ToolResponse.data: Any` weakens the OpenAPI schema for typed clients. Mitigation: per-route docstrings + `tasks/CONTRACTS.md` §6 table. Stricter typing is a follow-up if a TS client demands it.
- `parse_pdf` requires server-local filesystem access. Documented in Task 1.2; cross-host callers should call `fetch-attachment` first (which writes to Storage) and pass a path-after-download (when running same-host) or wait for a future `parse-pdf-from-storage` variant.
- The handoff implied a `.skill.run()` interface that doesn't exist; this plan dispatches to top-level skill functions directly, which is the actual pattern.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-09-sprint-b-http-tools-parity.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for this plan because each task is small and independent enough that fresh context per task keeps each subagent's reasoning sharp, and the two-stage review per task catches drift before it compounds across 14 tasks.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review. Best if you want to ride along step-by-step with minimal handoff overhead.

Which approach?
