# GovCapture MVP Completion — Part 2 (Phases 3–7)

Continuation of `2026-05-09-govcapture-mvp-completion.md`. Read Part 1 first.

---

# PHASE 3 — Discovery + Helper Skills

---

### Task 3.1: A11 `search_sam_opportunities`

**Endpoint:** SAM.gov v2 search.
**Fallback policy (PRD §5.4):** SAM 429 / 5xx → caller falls back to `load_seeded_opportunities`.

**Files:**
- Create: `api/skills/search_sam/__init__.py`
- Create: `api/skills/search_sam/skill.py`
- Create: `api/tests/test_search_sam.py`
- Modify: `pyproject.toml` — add `respx>=0.21` to dev deps

- [ ] **Step 1: Add `respx` to dev deps**

In `pyproject.toml`, add `"respx>=0.21"` under `[project.optional-dependencies].dev`. Then `uv sync --all-extras`.

- [ ] **Step 2: Tests**

`api/tests/test_search_sam.py`:

```python
import httpx
import pytest
import respx

from api.skills.search_sam import SearchSamInput, SearchSamSkill


@pytest.mark.asyncio
async def test_happy_path_returns_normalized_opportunities():
    async with respx.mock(assert_all_called=True) as m:
        m.get("https://api.sam.gov/opportunities/v2/search").respond(
            200,
            json={"opportunitiesData": [{
                "title": "Cloud Services",
                "noticeId": "ABC-001",
                "fullParentPathName": "DOD",
                "naicsCode": "541512",
                "typeOfSetAsideDescription": "Total Small Business",
                "responseDeadLine": "2026-06-15T17:00:00",
                "uiLink": "https://sam.gov/opp/abc",
                "description": "...",
            }]},
        )
        async with httpx.AsyncClient() as http:
            skill = SearchSamSkill(api_key="test", http=http)
            out = await skill.run(SearchSamInput(keywords="cloud", naics="541512"))
        assert len(out.opportunities) == 1
        assert out.opportunities[0]["solicitation_number"] == "ABC-001"
        assert out.degraded is False


@pytest.mark.asyncio
async def test_429_returns_degraded_with_empty_results():
    async with respx.mock(assert_all_called=True) as m:
        m.get("https://api.sam.gov/opportunities/v2/search").respond(429)
        async with httpx.AsyncClient() as http:
            skill = SearchSamSkill(api_key="test", http=http)
            out = await skill.run(SearchSamInput(keywords="x"))
        assert out.degraded is True
        assert out.opportunities == []
        assert "rate limit" in out.error.lower()
```

- [ ] **Step 3: Implement**

`api/skills/search_sam/skill.py`:

```python
"""search_sam_opportunities — SAM.gov v2 search with degraded-fallback."""
from __future__ import annotations

import httpx
from pydantic import BaseModel

SAM_URL = "https://api.sam.gov/opportunities/v2/search"


class SearchSamInput(BaseModel):
    keywords: str = ""
    naics: str | None = None
    posted_from: str | None = None
    set_aside: str | None = None
    state: str | None = None
    limit: int = 20


class SearchSamOutput(BaseModel):
    opportunities: list[dict] = []
    degraded: bool = False
    error: str = ""


class SearchSamSkill:
    def __init__(self, api_key: str, http: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._http = http

    async def run(self, payload: SearchSamInput) -> SearchSamOutput:
        params: dict[str, str | int] = {
            "api_key": self._api_key,
            "limit": payload.limit,
            "q": payload.keywords or "",
        }
        if payload.naics:
            params["naicsCode"] = payload.naics
        if payload.posted_from:
            params["postedFrom"] = payload.posted_from
        if payload.set_aside:
            params["typeOfSetAside"] = payload.set_aside
        if payload.state:
            params["state"] = payload.state

        try:
            resp = await self._http.get(SAM_URL, params=params, timeout=20.0)
        except httpx.HTTPError as exc:
            return SearchSamOutput(degraded=True, error=f"network: {exc}")

        if resp.status_code == 429:
            return SearchSamOutput(degraded=True, error="SAM rate limit (429)")
        if resp.status_code >= 500:
            return SearchSamOutput(degraded=True, error=f"SAM 5xx: {resp.status_code}")
        if resp.status_code >= 400:
            return SearchSamOutput(
                degraded=True, error=f"SAM client error: {resp.status_code}"
            )

        data = resp.json()
        normalized = [self._normalize(rec) for rec in data.get("opportunitiesData", [])]
        return SearchSamOutput(opportunities=normalized)

    @staticmethod
    def _normalize(rec: dict) -> dict:
        return {
            "title": rec.get("title", ""),
            "agency": rec.get("fullParentPathName", "").split(".")[0],
            "solicitation_number": rec.get("noticeId", ""),
            "source_url": rec.get("uiLink", ""),
            "due_date": (rec.get("responseDeadLine") or "")[:10],
            "naics": rec.get("naicsCode", ""),
            "set_aside": rec.get("typeOfSetAsideDescription", "") or "None",
            "place_of_performance": (
                (rec.get("placeOfPerformance") or {}).get("city", {}).get("name", "")
            ),
            "description": (rec.get("description") or "")[:1000],
            "attachments": [],
            "raw_payload": rec,
        }
```

`api/skills/search_sam/__init__.py`:

```python
from api.skills.search_sam.skill import SearchSamInput, SearchSamOutput, SearchSamSkill

__all__ = ["SearchSamInput", "SearchSamOutput", "SearchSamSkill"]
```

- [ ] **Step 4: Run + commit**

```bash
uv run pytest api/tests/test_search_sam.py -v
git add api/skills/search_sam/ api/tests/test_search_sam.py pyproject.toml uv.lock
git commit -m "feat(skills): A11 search_sam_opportunities with degraded fallback"
```

---

### Task 3.2: `fetch_attachment` skill

Download a PDF from a URL into Supabase Storage at `raw/<run_id>/<filename>.pdf`.

**Files:**
- Create: `api/skills/fetch_attachment/__init__.py`
- Create: `api/skills/fetch_attachment/skill.py`
- Create: `api/tests/test_fetch_attachment.py`

- [ ] **Step 1: Test**

`api/tests/test_fetch_attachment.py`:

```python
import httpx
import pytest
import respx

from api.skills.fetch_attachment import FetchAttachmentInput, FetchAttachmentSkill


class _FakeStorage:
    def __init__(self) -> None:
        self.uploaded: list[tuple[str, bytes]] = []

    async def upload_bytes(self, path: str, body: bytes) -> str:
        self.uploaded.append((path, body))
        return path


@pytest.mark.asyncio
async def test_downloads_and_uploads_to_storage():
    async with respx.mock(assert_all_called=True) as m:
        m.get("https://example.gov/rfp.pdf").respond(200, content=b"%PDF-1.4...")
        storage = _FakeStorage()
        async with httpx.AsyncClient() as http:
            skill = FetchAttachmentSkill(http=http, storage=storage)
            out = await skill.run(FetchAttachmentInput(
                run_id="abc", url="https://example.gov/rfp.pdf",
            ))
        assert out.storage_path == "raw/abc/rfp.pdf"
        assert storage.uploaded == [("raw/abc/rfp.pdf", b"%PDF-1.4...")]
```

- [ ] **Step 2: Implement**

`api/skills/fetch_attachment/skill.py`:

```python
"""fetch_attachment — download PDF and persist to Supabase Storage raw bucket."""
from __future__ import annotations

from typing import Protocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel


class _StorageProto(Protocol):
    async def upload_bytes(self, path: str, body: bytes) -> str: ...


class FetchAttachmentInput(BaseModel):
    run_id: str
    url: str
    filename: str | None = None


class FetchAttachmentOutput(BaseModel):
    storage_path: str
    bytes_downloaded: int


class FetchAttachmentSkill:
    def __init__(self, http: httpx.AsyncClient, storage: _StorageProto) -> None:
        self._http = http
        self._storage = storage

    async def run(self, payload: FetchAttachmentInput) -> FetchAttachmentOutput:
        resp = await self._http.get(
            payload.url, timeout=60.0, follow_redirects=True
        )
        resp.raise_for_status()
        body = resp.content
        filename = payload.filename or self._derive_name(payload.url)
        path = f"raw/{payload.run_id}/{filename}"
        await self._storage.upload_bytes(path, body)
        return FetchAttachmentOutput(
            storage_path=path, bytes_downloaded=len(body),
        )

    @staticmethod
    def _derive_name(url: str) -> str:
        parsed = urlparse(url).path
        name = parsed.rsplit("/", 1)[-1] or "attachment.pdf"
        return name if name.lower().endswith(".pdf") else f"{name}.pdf"
```

`api/skills/fetch_attachment/__init__.py`:

```python
from api.skills.fetch_attachment.skill import (
    FetchAttachmentInput, FetchAttachmentOutput, FetchAttachmentSkill,
)

__all__ = [
    "FetchAttachmentInput", "FetchAttachmentOutput", "FetchAttachmentSkill",
]
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest api/tests/test_fetch_attachment.py -v
git add api/skills/fetch_attachment/ api/tests/test_fetch_attachment.py
git commit -m "feat(skills): fetch_attachment — download PDF to Supabase Storage raw/"
```

---

### Task 3.3: `parse_goal` skill

Convert a natural-language goal → structured search criteria.

**Files:**
- Create: `api/skills/parse_goal/__init__.py`
- Create: `api/skills/parse_goal/skill.py`
- Create: `api/skills/parse_goal/prompt.txt`
- Create: `api/tests/test_parse_goal.py`

- [ ] **Step 1: Test**

`api/tests/test_parse_goal.py`:

```python
import pytest

from api.skills.parse_goal import ParseGoalInput, ParseGoalSkill
from api.tests.fakes import FakeLLM


@pytest.mark.asyncio
async def test_parses_typical_goal():
    fake_llm = FakeLLM(canned_response={
        "keywords": ["cybersecurity", "infosec"],
        "naics_hints": ["541512", "541519"],
        "due_window_days": 60,
        "set_aside_pref": "small_business",
        "geography": None,
        "agencies": None,
        "opportunity_type": "any",
    })
    skill = ParseGoalSkill(llm=fake_llm)
    out = await skill.run(ParseGoalInput(
        goal="Find cybersecurity opportunities we can pursue in the next 60 days.",
        company_profile={"name": "DemoCo", "naics_codes": ["541512"]},
    ))
    assert "cybersecurity" in out.keywords
    assert out.due_window_days == 60
```

- [ ] **Step 2: Prompt + implementation**

`api/skills/parse_goal/prompt.txt`:

```
### SYSTEM ###
You parse a small business owner's contracting goal into structured search criteria.

Always return JSON with these fields (use null when unknown):
- keywords: list of 3-8 strings
- naics_hints: list of NAICS codes (strings) — empty if none implied
- due_window_days: integer — interpret "next N days/weeks/months", default 30
- set_aside_pref: "small_business" | "8a" | "wosb" | "hubzone" | "sdvosb" | null
- geography: state code or city name | null
- agencies: list of agency names mentioned | null
- opportunity_type: "any" | "rfp" | "rfi" | "sources_sought"

Be conservative. If unclear, leave null.

### USER ###
Goal: {goal}
Company NAICS: {naics_codes}
```

`api/skills/parse_goal/skill.py`:

```python
"""parse_goal — natural-language goal → structured search criteria."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from api.llm import LLM, LLMMetrics

PROMPT_PATH = Path(__file__).parent / "prompt.txt"
RAW_PROMPT = PROMPT_PATH.read_text()
_SYSTEM_TAG = "### SYSTEM ###"
_USER_TAG = "### USER ###"
SYSTEM_PROMPT = RAW_PROMPT.split(_SYSTEM_TAG, 1)[1].split(_USER_TAG, 1)[0].strip()
USER_TEMPLATE = RAW_PROMPT.split(_USER_TAG, 1)[1].strip()


class ParseGoalInput(BaseModel):
    goal: str
    company_profile: dict[str, Any]


class ParseGoalOutput(BaseModel):
    keywords: list[str]
    naics_hints: list[str]
    due_window_days: int
    set_aside_pref: str | None
    geography: str | None
    agencies: list[str] | None
    opportunity_type: str
    metrics: LLMMetrics


_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["keywords", "naics_hints", "due_window_days", "opportunity_type"],
    "properties": {
        "keywords": {"type": "array", "items": {"type": "string"}},
        "naics_hints": {"type": "array", "items": {"type": "string"}},
        "due_window_days": {"type": "integer", "minimum": 1, "maximum": 365},
        "set_aside_pref": {"type": ["string", "null"]},
        "geography": {"type": ["string", "null"]},
        "agencies": {"type": ["array", "null"]},
        "opportunity_type": {"type": "string"},
    },
}


class ParseGoalSkill:
    def __init__(self, llm: LLM) -> None:
        self._llm = llm

    async def run(self, payload: ParseGoalInput) -> ParseGoalOutput:
        user_prompt = USER_TEMPLATE.format(
            goal=payload.goal,
            naics_codes=payload.company_profile.get("naics_codes", []),
        )
        result, metrics = await self._llm.complete_structured(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            schema=_OUTPUT_SCHEMA,
        )
        return ParseGoalOutput(**result, metrics=metrics)
```

`api/skills/parse_goal/__init__.py`:

```python
from api.skills.parse_goal.skill import ParseGoalInput, ParseGoalOutput, ParseGoalSkill

__all__ = ["ParseGoalInput", "ParseGoalOutput", "ParseGoalSkill"]
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest api/tests/test_parse_goal.py -v
git add api/skills/parse_goal/ api/tests/test_parse_goal.py
git commit -m "feat(skills): parse_goal — natural-language goal → search criteria"
```

---

### Task 3.4: `rank_opportunities` skill

Pure deterministic — no LLM. Sort by `(decision_band_priority, total_score desc, due_date asc)`.

**Files:**
- Create: `api/skills/rank_opportunities/__init__.py`
- Create: `api/skills/rank_opportunities/skill.py`
- Create: `api/tests/test_rank_opportunities.py`

- [ ] **Step 1: Test**

```python
from api.skills.rank_opportunities import RankInput, RankOpportunitiesSkill


def test_ranks_by_band_then_score_then_deadline():
    skill = RankOpportunitiesSkill()
    scored = [
        {"opportunity_id": "a", "decision": "maybe", "total_score": 60, "due_date": "2026-06-01"},
        {"opportunity_id": "b", "decision": "strong_pursue", "total_score": 88, "due_date": "2026-07-01"},
        {"opportunity_id": "c", "decision": "strong_pursue", "total_score": 92, "due_date": "2026-08-01"},
        {"opportunity_id": "d", "decision": "reject", "total_score": 0, "due_date": "2026-05-15"},
    ]
    out = skill.run(RankInput(scored=scored))
    assert [r["opportunity_id"] for r in out.ranked] == ["c", "b", "a", "d"]
```

- [ ] **Step 2: Implement**

`api/skills/rank_opportunities/skill.py`:

```python
"""rank_opportunities — deterministic ordering for the timeline UI."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

BAND_ORDER = {"strong_pursue": 0, "pursue": 1, "maybe": 2, "reject": 3}


class RankInput(BaseModel):
    scored: list[dict[str, Any]]


class RankOutput(BaseModel):
    ranked: list[dict[str, Any]]


class RankOpportunitiesSkill:
    def run(self, payload: RankInput) -> RankOutput:
        return RankOutput(
            ranked=sorted(
                payload.scored,
                key=lambda x: (
                    BAND_ORDER.get(x.get("decision"), 99),
                    -int(x.get("total_score", 0)),
                    x.get("due_date", "9999-12-31"),
                ),
            )
        )
```

`api/skills/rank_opportunities/__init__.py`:

```python
from api.skills.rank_opportunities.skill import (
    RankInput, RankOpportunitiesSkill, RankOutput,
)

__all__ = ["RankInput", "RankOpportunitiesSkill", "RankOutput"]
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest api/tests/test_rank_opportunities.py -v
git add api/skills/rank_opportunities/ api/tests/test_rank_opportunities.py
git commit -m "feat(skills): rank_opportunities — deterministic band-then-score ordering"
```

---

# PHASE 4 — Hermes Integration

**Architecture (per `tasks/HERMES.md`):** Hermes runs as a **local subprocess**. Local install at `~/.local/bin/hermes` (v0.13.0); on VX1 installed by `infra/bootstrap.sh`. FastAPI spawns Hermes per run, hands it a goal + skills manifest, and:
- **Tool callbacks:** Hermes calls back into FastAPI over HTTP (`POST /agent/tool-call`) when it wants to invoke a registered domain skill.
- **Trace events:** Hermes emits structured events to stdout (NDJSON); the runner forwards them to a Redis pub/sub channel after translation to CONTRACTS.md §3 shape.

**Replayer is kept** behind `USE_REPLAYER=true` until Phase 4 is green end-to-end. Phase 7 deletes it.

The 8 SKILL manifests at `.hermes/skills/govcapture/<skill>/SKILL.md` already exist (commit history shows them under `tasks/dev1-backend/skeletons/`). Phase 4 audits and updates them rather than creating from scratch.

---

### Task 4.0: Pre-flight — Hermes binary smoke test + protocol doc

**Why:** Capture the exact JSON contract Hermes uses (input format, event format, return value) before writing any glue. The dev install at `~/.local/bin/hermes` v0.13.0 is what ships.

**Files:**
- Create: `tasks/HERMES_PROTOCOL.md` — captured from a manual run

- [ ] **Step 1: Run hermes against a no-op skill manifest**

```bash
hermes --version
hermes --help 2>&1 | head -50
hermes run --help 2>&1 | head -30
```

- [ ] **Step 2: Capture the input/output schema and event shape**

Document in `tasks/HERMES_PROTOCOL.md`:
- Exact CLI invocation: `hermes run --skills <dir> --input <json>` or whatever the v0.13.0 CLI uses
- stdout event format (NDJSON?) — kinds, fields, ordering
- stderr usage
- Exit codes
- HTTP tool-callback expectations (URL, headers, request/response shape)
- Working directory expectations / `HERMES_HOME` usage

- [ ] **Step 3: Commit the protocol doc**

```bash
git add tasks/HERMES_PROTOCOL.md
git commit -m "docs(hermes): captured CLI protocol for v0.13.0 integration"
```

> **Branch in plan:** Tasks 4.1–4.4 below assume a CLI-with-NDJSON-events shape (the most common Hermes pattern). If 4.0 reveals a substantially different protocol, adjust the runner code; the bridge translation logic stays the same.

---

### Task 4.1: `hermes_runner` — subprocess invocation

**Files:**
- Create: `api/agent/hermes_runner.py`
- Create: `api/agent/skill_registry.py`
- Create: `api/agent/tool_callback.py`
- Modify: `api/config.py` — add `USE_REPLAYER`, `HERMES_BINARY`, `HERMES_HOME`, `TOOL_CALLBACK_URL`

- [ ] **Step 1: Add config knobs**

In `api/config.py`, append to `Settings`:

```python
use_replayer: bool = Field(False, alias="USE_REPLAYER")
hermes_binary: str = Field("hermes", alias="HERMES_BINARY")
hermes_home: str = Field("", alias="HERMES_HOME")  # empty = let hermes default
tool_callback_url: str = Field("http://127.0.0.1:8000", alias="TOOL_CALLBACK_URL")
```

- [ ] **Step 2: Skill registry — describe each skill's name + JSON Schema**

`api/agent/skill_registry.py`:

```python
"""Build the Hermes skill manifest list (one entry per domain skill)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

# Manifest entries are written to disk per the format Hermes expects (see
# tasks/HERMES_PROTOCOL.md captured by Task 4.0). This module does NOT
# instantiate skills — those are instantiated in tool_callback.py when
# Hermes calls back. The registry merely declares what is available.

SKILL_MANIFESTS: list[dict[str, Any]] = [
    {
        "name": "parse_goal",
        "description": "Convert a natural-language goal to structured search criteria.",
        "input_schema": {
            "type": "object",
            "required": ["goal", "company_profile"],
            "properties": {
                "goal": {"type": "string"},
                "company_profile": {"type": "object"},
            },
        },
    },
    {
        "name": "search_sam",
        "description": "Query SAM.gov v2 search API.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {"type": "string"},
                "naics": {"type": ["string", "null"]},
                "set_aside": {"type": ["string", "null"]},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "load_seeded_opportunities",
        "description": "Load fixture opportunities from /fixtures into the database.",
        "input_schema": {
            "type": "object",
            "properties": {"slugs": {"type": ["array", "null"]}},
        },
    },
    {
        "name": "fetch_attachment",
        "description": "Download a PDF to Supabase Storage raw bucket.",
        "input_schema": {
            "type": "object",
            "required": ["run_id", "url"],
            "properties": {
                "run_id": {"type": "string"},
                "url": {"type": "string"},
                "filename": {"type": ["string", "null"]},
            },
        },
    },
    {
        "name": "parse_pdf",
        "description": "Extract page-level text from a PDF; returns unparseable=true on image-only.",
        "input_schema": {
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string"}},
        },
    },
    {
        "name": "extract_requirements",
        "description": "Extract structured requirements from parsed PDF chunks.",
        "input_schema": {
            "type": "object",
            "required": ["parsed_chunks"],
            "properties": {"parsed_chunks": {"type": "array"}},
        },
    },
    {
        "name": "score_fit",
        "description": "Score opportunity fit (§5.7); enforces §11.1 short-circuit deterministically.",
        "input_schema": {
            "type": "object",
            "required": ["company_profile", "requirements"],
            "properties": {
                "company_profile": {"type": "object"},
                "requirements": {"type": "array"},
            },
        },
    },
    {
        "name": "detect_risks",
        "description": "Detect risks per §5.8 taxonomy.",
        "input_schema": {
            "type": "object",
            "required": ["company_profile", "requirements", "opportunity"],
            "properties": {
                "company_profile": {"type": "object"},
                "requirements": {"type": "array"},
                "opportunity": {"type": "object"},
            },
        },
    },
    {
        "name": "generate_action_package",
        "description": "Synthesize the action package (modes: full, reject_summary).",
        "input_schema": {
            "type": "object",
            "required": ["mode", "company_profile", "opportunity",
                         "requirements", "fit_score", "risks"],
            "properties": {
                "mode": {"enum": ["full", "reject_summary"]},
                "company_profile": {"type": "object"},
                "opportunity": {"type": "object"},
                "requirements": {"type": "array"},
                "fit_score": {"type": "object"},
                "risks": {"type": "array"},
            },
        },
    },
    {
        "name": "rank_opportunities",
        "description": "Order scored opportunities for the timeline.",
        "input_schema": {
            "type": "object",
            "required": ["scored"],
            "properties": {"scored": {"type": "array"}},
        },
    },
    {
        "name": "request_human_review",
        "description": "Pause the run; surface a question + context to the user.",
        "input_schema": {
            "type": "object",
            "required": ["run_id", "question", "context"],
            "properties": {
                "run_id": {"type": "string"},
                "question": {"type": "string"},
                "context": {"type": "object"},
            },
        },
    },
]


def write_manifest_file(target: Path) -> None:
    """Materialize the skill manifest in the format Hermes expects.

    The exact on-disk format is determined by Task 4.0's protocol capture.
    Most likely a JSON file at $HERMES_HOME/skills/govcapture/skills.json
    or one .md per skill. Implement after 4.0 is committed.
    """
    raise NotImplementedError("Implement after Task 4.0 protocol capture.")
```

- [ ] **Step 3: Tool-callback HTTP endpoint — Hermes calls back into FastAPI**

`api/agent/tool_callback.py`:

```python
"""HTTP endpoint Hermes calls back into to invoke a registered domain skill.

Wiring:
- Hermes is started by hermes_runner with TOOL_CALLBACK_URL pointing at us.
- When the planner decides to call a skill, Hermes POSTs:
    POST /agent/tool-call
    { "run_id": "...", "skill": "score_fit", "input": { ... } }
- We dispatch to the right domain skill, return the result JSON.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.config import settings
from api.deps import (
    get_company_profile_repo, get_http_client, get_llm, get_opportunity_repo,
    get_storage_client,
)
from api.repositories.company_profile import CompanyProfileRepo
from api.repositories.opportunity import OpportunityRepo
from api.skills.detect_risks import DetectRisksInput, DetectRisksSkill
from api.skills.extract_requirements import (
    ExtractRequirementsInput, ExtractRequirementsSkill,
)
from api.skills.fetch_attachment import FetchAttachmentInput, FetchAttachmentSkill
from api.skills.generate_action_package import (
    GenerateActionPackageInput, GenerateActionPackageSkill,
)
from api.skills.load_seeded_opportunities import LoadSeededInput, LoadSeededSkill
from api.skills.parse_goal import ParseGoalInput, ParseGoalSkill
from api.skills.parse_pdf import ParsePdfInput, ParsePdfSkill
from api.skills.rank_opportunities import RankInput, RankOpportunitiesSkill
from api.skills.score_fit import ScoreFitInput, ScoreFitSkill
from api.skills.search_sam import SearchSamInput, SearchSamSkill

router = APIRouter(prefix="/agent", tags=["agent"])


class ToolCallRequest(BaseModel):
    run_id: str
    skill: str
    input: dict[str, Any]


@router.post("/tool-call")
async def tool_call(
    payload: ToolCallRequest,
    llm=Depends(get_llm),
    http: httpx.AsyncClient = Depends(get_http_client),
    storage=Depends(get_storage_client),
    opp_repo: OpportunityRepo = Depends(get_opportunity_repo),
    profile_repo: CompanyProfileRepo = Depends(get_company_profile_repo),
):
    skill_name = payload.skill
    inp = payload.input
    try:
        if skill_name == "parse_goal":
            out = await ParseGoalSkill(llm=llm).run(ParseGoalInput(**inp))
        elif skill_name == "search_sam":
            out = await SearchSamSkill(api_key=settings.sam_api_key, http=http).run(
                SearchSamInput(**inp)
            )
        elif skill_name == "load_seeded_opportunities":
            out = await LoadSeededSkill(
                opportunity_repo=opp_repo, fixtures_dir=Path("fixtures")
            ).run(LoadSeededInput(**inp))
        elif skill_name == "fetch_attachment":
            out = await FetchAttachmentSkill(http=http, storage=storage).run(
                FetchAttachmentInput(**inp)
            )
        elif skill_name == "parse_pdf":
            out = await ParsePdfSkill().run(ParsePdfInput(**inp))
        elif skill_name == "extract_requirements":
            out = await ExtractRequirementsSkill(llm=llm).run(
                ExtractRequirementsInput(**inp)
            )
        elif skill_name == "score_fit":
            out = await ScoreFitSkill(llm=llm).run(ScoreFitInput(**inp))
        elif skill_name == "detect_risks":
            out = await DetectRisksSkill(llm=llm).run(DetectRisksInput(**inp))
        elif skill_name == "generate_action_package":
            out = await GenerateActionPackageSkill(llm=llm).run(
                GenerateActionPackageInput(**inp)
            )
        elif skill_name == "rank_opportunities":
            out = RankOpportunitiesSkill().run(RankInput(**inp))
        elif skill_name == "request_human_review":
            from api.skills.request_human_review import (  # implemented in Task 4.5
                RequestHumanReviewInput, RequestHumanReviewSkill,
            )
            out = await RequestHumanReviewSkill().run(
                RequestHumanReviewInput(**inp)
            )
        else:
            raise HTTPException(404, f"Unknown skill: {skill_name}")
    except Exception as exc:  # noqa: BLE001 — wrap for the planner
        raise HTTPException(500, str(exc)) from exc

    return out.model_dump() if hasattr(out, "model_dump") else out
```

- [ ] **Step 4: hermes_runner.py — orchestrate one run**

`api/agent/hermes_runner.py`:

```python
"""Start a Hermes subprocess for a run; bridge its stdout NDJSON to Redis."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from uuid import UUID

import redis.asyncio as aioredis

from api.agent.hermes_bridge import translate
from api.config import settings

logger = logging.getLogger(__name__)


async def run_capture(
    run_id: UUID,
    goal: str,
    company_profile: dict,
    redis_client: aioredis.Redis,
) -> None:
    """Spawn hermes as a subprocess; forward translated events to Redis."""
    # Build the input JSON Hermes consumes (exact shape captured in Task 4.0).
    payload = {
        "run_id": str(run_id),
        "goal": goal,
        "company_profile": company_profile,
        "tool_callback_url": settings.tool_callback_url,
        "skill_manifest_path": ".hermes/skills/govcapture",
    }
    env = {**os.environ, **({"HERMES_HOME": settings.hermes_home} if settings.hermes_home else {})}
    cmd = [settings.hermes_binary, "run", "--skill-pack", "govcapture", "--json"]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    assert proc.stdin and proc.stdout
    proc.stdin.write(json.dumps(payload).encode() + b"\n")
    await proc.stdin.drain()
    proc.stdin.close()

    channel = f"agent-run:{run_id}"
    try:
        await asyncio.wait_for(
            _bridge_stdout(proc.stdout, run_id, redis_client, channel),
            timeout=settings.run_budget_seconds,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await redis_client.publish(channel, json.dumps({
            "type": "run_completed",
            "run_id": str(run_id),
            "status": "partial",
            "summary": "Wall-clock budget exceeded.",
            "ts": _now_iso(),
        }))
        return
    finally:
        rc = await proc.wait()
        if rc != 0:
            err = (await proc.stderr.read()).decode(errors="replace") if proc.stderr else ""
            logger.error("hermes_nonzero_exit", extra={"run_id": str(run_id), "rc": rc, "stderr": err[:2000]})


async def _bridge_stdout(stdout, run_id: UUID, redis_client, channel: str) -> None:
    while True:
        line = await stdout.readline()
        if not line:
            return
        try:
            hermes_event = json.loads(line.decode())
        except json.JSONDecodeError:
            logger.warning("hermes_bad_ndjson", extra={"raw": line[:200]})
            continue
        translated = translate(hermes_event, run_id=str(run_id))
        if translated is None:
            continue
        await redis_client.publish(channel, json.dumps(translated))
        if translated["type"] == "run_completed":
            return


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
```

- [ ] **Step 5: Tests — mock subprocess + Redis**

Write `api/tests/test_hermes_runner.py` that monkeypatches `asyncio.create_subprocess_exec` to return a fake process whose `stdout` yields known NDJSON lines, and a fake Redis recording publishes. Assert the translated events match CONTRACTS.md §3 shapes.

- [ ] **Step 6: Commit**

```bash
git add api/agent/skill_registry.py api/agent/hermes_runner.py api/agent/tool_callback.py api/tests/test_hermes_runner.py api/config.py
git commit -m "feat(agent): A9 hermes_runner + skill_registry + tool_callback HTTP endpoint"
```

---

### Task 4.2: `hermes_bridge` — translate Hermes events to CONTRACTS.md §3 SSE

**Files:**
- Create: `api/agent/hermes_bridge.py`
- Create: `api/tests/test_hermes_bridge.py`
- Modify: `schemas/trace-event.schema.json` — add `subagent_spawned` and `subagent_completed`
- Modify: `schemas/trace-event.example.jsonl` — add example records for new event types

- [ ] **Step 1: Tests**

`api/tests/test_hermes_bridge.py`:

```python
from api.agent.hermes_bridge import translate


def test_translate_step_start_to_step_started():
    he = {
        "kind": "step.start", "step_id": "s1",
        "label": "search opportunities",
        "timestamp": "2026-05-09T12:00:00Z",
    }
    out = translate(he, run_id="run-1")
    assert out["type"] == "step_started"
    assert out["step_id"] == "s1"
    assert out["label"] == "search opportunities"
    assert out["run_id"] == "run-1"


def test_translate_tool_call_to_tool_called():
    he = {
        "kind": "tool.call", "step_id": "s2", "tool": "parse_pdf",
        "input": {"path": "x.pdf"}, "rationale": "need to extract text",
        "timestamp": "2026-05-09T12:00:01Z",
    }
    out = translate(he, run_id="run-1")
    assert out["type"] == "tool_called"
    assert out["tool"] == "parse_pdf"


def test_translate_subagent_spawn_emits_subagent_event():
    he = {
        "kind": "agent.spawn", "agent_role": "capture_analyst",
        "child_id": "ca-1", "parent_id": "cl-0",
        "timestamp": "2026-05-09T12:00:02Z",
    }
    out = translate(he, run_id="run-1")
    assert out["type"] == "subagent_spawned"
    assert out["agent_role"] == "capture_analyst"


def test_unknown_event_returns_none():
    he = {"kind": "telemetry.gauge", "name": "x", "value": 1}
    assert translate(he, run_id="run-1") is None
```

- [ ] **Step 2: Implement**

`api/agent/hermes_bridge.py`:

```python
"""Translate Hermes internal trace events to CONTRACTS.md §3 wire shapes."""
from __future__ import annotations

EVENT_MAP = {
    "run.start": "run_started",
    "run.complete": "run_completed",
    "step.start": "step_started",
    "step.complete": "step_completed",
    "tool.call": "tool_called",
    "tool.return": "tool_returned",
    "decision.opportunity_ranked": "opportunity_ranked",
    "human.review_requested": "needs_human",
    "agent.spawn": "subagent_spawned",
    "agent.complete": "subagent_completed",
}


def translate(hermes_event: dict, run_id: str) -> dict | None:
    """Map a Hermes event dict to a CONTRACTS.md §3 event dict, or None.

    Returning None means the event is internal-only and should not reach SSE.
    """
    kind = hermes_event.get("kind", "")
    out_type = EVENT_MAP.get(kind)
    if not out_type:
        return None
    base: dict = {
        "type": out_type,
        "run_id": run_id,
        "ts": hermes_event.get("timestamp", ""),
    }
    if out_type in {"step_started", "step_completed"}:
        base["step_id"] = hermes_event["step_id"]
        if out_type == "step_started":
            base["label"] = hermes_event.get("label", "")
        else:
            base["status"] = hermes_event.get("status", "complete")
    elif out_type == "tool_called":
        base.update({
            "step_id": hermes_event["step_id"],
            "tool": hermes_event["tool"],
            "input": hermes_event.get("input", {}),
            "rationale": hermes_event.get("rationale", ""),
        })
    elif out_type == "tool_returned":
        base.update({
            "step_id": hermes_event["step_id"],
            "tool": hermes_event["tool"],
            "output": hermes_event.get("output"),
            "error": hermes_event.get("error"),
            "latency_ms": hermes_event.get("latency_ms", 0),
            "cost_usd": hermes_event.get("cost_usd", 0.0),
        })
    elif out_type == "opportunity_ranked":
        base.update({
            "opportunity_id": hermes_event["opportunity_id"],
            "score": hermes_event["score"],
            "decision": hermes_event["decision"],
        })
    elif out_type == "needs_human":
        base.update({
            "question": hermes_event.get("question", ""),
            "context": hermes_event.get("context", {}),
        })
    elif out_type == "subagent_spawned":
        base.update({
            "agent_role": hermes_event.get("agent_role"),
            "child_id": hermes_event.get("child_id"),
            "parent_id": hermes_event.get("parent_id"),
        })
    elif out_type == "subagent_completed":
        base.update({
            "child_id": hermes_event.get("child_id"),
            "status": hermes_event.get("status", "complete"),
        })
    elif out_type == "run_started":
        base.update({
            "goal": hermes_event.get("goal", ""),
            "profile_id": hermes_event.get("profile_id", ""),
        })
    elif out_type == "run_completed":
        base.update({
            "status": hermes_event.get("status", "complete"),
            "summary": hermes_event.get("summary", ""),
        })
    return base
```

- [ ] **Step 3: Extend the trace-event schema with two new event types**

In `schemas/trace-event.schema.json` `oneOf` array, append:

```json
{
  "type": "object",
  "required": ["type", "run_id", "agent_role", "child_id", "parent_id", "ts"],
  "properties": {
    "type": {"const": "subagent_spawned"},
    "run_id": {"type": "string"},
    "agent_role": {"enum": ["capture_lead", "capture_analyst",
        "compliance_officer", "risk_analyst", "proposal_strategist"]},
    "child_id": {"type": "string"},
    "parent_id": {"type": "string"},
    "ts": {"type": "string"}
  }
},
{
  "type": "object",
  "required": ["type", "run_id", "child_id", "status", "ts"],
  "properties": {
    "type": {"const": "subagent_completed"},
    "run_id": {"type": "string"},
    "child_id": {"type": "string"},
    "status": {"enum": ["complete", "failed", "timeout"]},
    "ts": {"type": "string"}
  }
}
```

- [ ] **Step 4: Add example records for new event types**

Append two lines to `schemas/trace-event.example.jsonl`:

```jsonl
{"type":"subagent_spawned","run_id":"00000000-0000-0000-0000-000000000000","agent_role":"capture_analyst","child_id":"ca-1","parent_id":"cl-0","ts":"2026-05-09T12:00:02Z"}
{"type":"subagent_completed","run_id":"00000000-0000-0000-0000-000000000000","child_id":"ca-1","status":"complete","ts":"2026-05-09T12:00:30Z"}
```

- [ ] **Step 5: Regenerate schemas + run**

```bash
make schemas
uv run pytest api/tests/test_hermes_bridge.py api/tests/test_schemas.py -v
git add api/agent/hermes_bridge.py api/tests/test_hermes_bridge.py schemas/ api/schemas/
git commit -m "feat(agent): hermes_bridge — Hermes events → CONTRACTS.md §3 SSE"
```

---

### Task 4.3: Audit existing Hermes skill manifests

The 8 SKILL.md files at `.hermes/skills/govcapture/` already exist. Audit each for:
- Tool whitelist matches the new skill names from Phase 2/3
- Delegation chain matches `tasks/AGENT_ARCHITECTURE.md` (Capture Lead → Capture Analyst → Specialist, depth ≤ 2)
- Reject-mode strategist (`generate_reject_summary`) sets the LLM to none
- Each manifest references skills by the names registered in `skill_registry.SKILL_MANIFESTS`

**Files:**
- Modify: `.hermes/skills/govcapture/operate_bid_desk/SKILL.md`
- Modify: `.hermes/skills/govcapture/discover_opportunities/SKILL.md`
- Modify: `.hermes/skills/govcapture/analyze_opportunity_e2e/SKILL.md`
- Modify: `.hermes/skills/govcapture/extract_requirements_with_evidence/SKILL.md`
- Modify: `.hermes/skills/govcapture/score_fit_with_eligibility_check/SKILL.md`
- Modify: `.hermes/skills/govcapture/detect_risks_calibrated/SKILL.md`
- Modify: `.hermes/skills/govcapture/generate_full_action_package/SKILL.md`
- Modify: `.hermes/skills/govcapture/generate_reject_summary/SKILL.md`

- [ ] **Step 1: Audit each manifest**

For each file: read it, check that the `tools:` list references the new skill names (`parse_goal`, `search_sam`, etc.), check the `delegates_to:` chain. Update where stale.

- [ ] **Step 2: Verify config.yaml**

Confirm `.hermes/config.yaml` has `delegation.max_spawn_depth: 2` and `delegation.max_concurrent_children: 3` (already done per inherited state).

- [ ] **Step 3: Smoke-test with a no-op fixture**

```bash
hermes run --skill-pack govcapture --dry-run < /dev/null 2>&1 | head -20
```

- [ ] **Step 4: Commit any changes**

```bash
git add .hermes/skills/govcapture/
git commit -m "feat(agent): audit + update Hermes skill manifests for Phase 4 wiring"
```

---

### Task 4.4: Replace replayer call-site with hermes_runner (gated)

**Files:**
- Modify: `api/routes/agent_runs.py`
- Modify: `api/main.py` — register `tool_callback.router`

- [ ] **Step 1: Register the tool-callback router**

In `api/main.py`:

```python
from api.agent.tool_callback import router as tool_callback_router
app.include_router(tool_callback_router)
```

- [ ] **Step 2: Gate runner choice on `USE_REPLAYER`**

In `api/routes/agent_runs.py`, inside the POST handler that currently calls `replay_example_run`:

```python
from api.agent.hermes_runner import run_capture
from api.agent.replay import replay_example_run
from api.config import settings

# ... inside the handler:
if settings.use_replayer:
    background_tasks.add_task(replay_example_run, redis_client, run.id)
else:
    background_tasks.add_task(
        run_capture,
        run_id=run.id,
        goal=payload.goal,
        company_profile=profile.model_dump(),
        redis_client=redis_client,
    )
```

- [ ] **Step 3: Update existing SSE test**

The current SSE test relies on the replayer. Either:
- Run it with `USE_REPLAYER=true` (env var) — easier, validates the replayer path stays green
- Or write a new SSE test that mocks `run_capture` and publishes a known sequence

Pick the env-var approach for now; Phase 7 deletes the replayer.

- [ ] **Step 4: Commit**

```bash
git add api/routes/agent_runs.py api/main.py
git commit -m "feat(agent): gate hermes_runner vs replayer on USE_REPLAYER flag"
```

---

### Task 4.5: A10 `request_human_review` — pause-and-resume

When confidence collapses or §5.13 sensitive action is needed, the agent pauses. Run state moves to `awaiting_review`. Frontend shows the question + context. User answers via `POST /agent-runs/{id}/resume`.

**Files:**
- Modify: `schemas/agent-run.schema.json` — add `paused_at`, `pending_question`, `pending_context`, `human_response` fields
- Create: Alembic migration `0003_human_review.py`
- Modify: `api/db/models.py` — add fields to `AgentRun`
- Create: `api/skills/request_human_review/__init__.py`
- Create: `api/skills/request_human_review/skill.py`
- Modify: `api/repositories/agent_run.py` — add `pause_for_review`, `record_human_response`
- Modify: `api/routes/agent_runs.py` — add `POST /{id}/resume`
- Create: `api/tests/test_human_review.py`

- [ ] **Step 1: Update agent-run schema**

In `schemas/agent-run.schema.json`, add to `properties`:

```json
"paused_at": {"type": ["string", "null"], "format": "date-time"},
"pending_question": {"type": ["string", "null"]},
"pending_context": {"type": ["object", "null"]},
"human_response": {"type": ["object", "null"]}
```

Then `make schemas` to regen Pydantic.

- [ ] **Step 2: Generate migration**

```bash
make migration MSG="add human review pause fields to agent_runs"
```

Edit the generated `api/migrations/versions/0003_*.py`:

```python
def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agent_runs", sa.Column("pending_question", sa.Text, nullable=True))
    op.add_column("agent_runs", sa.Column("pending_context", postgresql.JSONB, nullable=True))
    op.add_column("agent_runs", sa.Column("human_response", postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "human_response")
    op.drop_column("agent_runs", "pending_context")
    op.drop_column("agent_runs", "pending_question")
    op.drop_column("agent_runs", "paused_at")
```

- [ ] **Step 3: Update model**

In `api/db/models.py`, add to `AgentRun`:

```python
paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
pending_question: Mapped[str | None] = mapped_column(Text, nullable=True)
pending_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
human_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

- [ ] **Step 4: Implement skill**

`api/skills/request_human_review/skill.py`:

```python
"""request_human_review — halt run, surface question to the user."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from api.repositories.agent_run import AgentRunRepo


class RequestHumanReviewInput(BaseModel):
    run_id: UUID
    question: str
    context: dict[str, Any]


class RequestHumanReviewOutput(BaseModel):
    paused: bool


class RequestHumanReviewSkill:
    def __init__(self, agent_run_repo: AgentRunRepo) -> None:
        self._repo = agent_run_repo

    async def run(self, payload: RequestHumanReviewInput) -> RequestHumanReviewOutput:
        await self._repo.pause_for_review(
            run_id=payload.run_id,
            question=payload.question,
            context=payload.context,
        )
        return RequestHumanReviewOutput(paused=True)
```

- [ ] **Step 5: Repo additions**

In `api/repositories/agent_run.py`:

```python
from datetime import datetime, timezone

async def pause_for_review(
    self, run_id: UUID, question: str, context: dict
) -> None:
    run = await self.get(run_id)
    if not run:
        raise ValueError(f"run {run_id} not found")
    run.paused_at = datetime.now(timezone.utc)
    run.pending_question = question
    run.pending_context = context

async def record_human_response(self, run_id: UUID, answer: dict) -> None:
    run = await self.get(run_id)
    if not run:
        raise ValueError(f"run {run_id} not found")
    run.human_response = answer
    run.paused_at = None
    run.pending_question = None
    run.pending_context = None
```

- [ ] **Step 6: Resume endpoint**

In `api/routes/agent_runs.py`:

```python
class ResumeRunRequest(BaseModel):
    answer: dict[str, Any]


@router.post("/{run_id}/resume", status_code=200)
async def resume_run(
    run_id: UUID,
    payload: ResumeRunRequest,
    background_tasks: BackgroundTasks,
    repo: AgentRunRepo = Depends(get_agent_run_repo),
    redis_client=Depends(get_redis_client),
):
    run = await repo.get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if not run.paused_at:
        raise HTTPException(409, "Run is not paused.")
    await repo.record_human_response(run_id, payload.answer)
    # NOTE: resuming a Hermes subprocess is non-trivial; for MVP we re-spawn
    # with the original goal + the human answer in context, and let the agent
    # reconsider. Mark this task complete in the next pass if Hermes v0.13.0
    # supports session resume natively.
    return {"resumed": True, "run_id": str(run_id)}
```

- [ ] **Step 7: Test the full pause/resume cycle**

`api/tests/test_human_review.py`:

```python
@pytest.mark.asyncio
async def test_request_human_review_pauses_run(client, db_session):
    # Seed a run.
    # Invoke the skill via direct call.
    # Verify run.paused_at is set in DB.
    # POST /agent-runs/{id}/resume.
    # Verify run.paused_at is cleared, human_response stored.
    ...
```

- [ ] **Step 8: Commit**

```bash
make migrate  # apply 0003
git add schemas/ api/skills/request_human_review/ api/migrations/versions/0003_*.py api/db/models.py api/repositories/agent_run.py api/routes/agent_runs.py api/tests/test_human_review.py api/schemas/
git commit -m "feat(skills): A10 request_human_review with pause/resume API"
```

---

# PHASE 5 — Eval Harness (A12)

PRD §19. Per-fixture golden assertions. `make eval` is the pre-demo smoke test.

---

### Task 5.1: Eval runner skeleton

**Files:**
- Create: `eval/runner/__init__.py`
- Create: `eval/runner/run.py`
- Create: `eval/runner/assertions.py`
- Create: `eval/goldens/strong-pursue.json`
- Create: `eval/goldens/maybe.json`
- Create: `eval/goldens/reject.json`
- Create: `eval/goldens/adversarial-image-pdf.json`
- Modify: `Makefile` — add `eval` target

- [ ] **Step 1: Runner**

`eval/runner/run.py`:

```python
"""Eval runner — load fixtures, run skills, assert against goldens."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from api.config import settings
from api.llm import LLM
from api.skills.detect_risks import DetectRisksInput, DetectRisksSkill
from api.skills.extract_requirements import (
    ExtractRequirementsInput, ExtractRequirementsSkill,
)
from api.skills.generate_action_package import (
    GenerateActionPackageInput, GenerateActionPackageSkill,
)
from api.skills.parse_pdf import ParsePdfInput, ParsePdfSkill
from api.skills.score_fit import ScoreFitInput, ScoreFitSkill
from eval.runner.assertions import assert_fixture

DEMO_COMPANY = {
    "name": "DemoCo",
    "naics_codes": ["541512"],
    "certifications": ["CMMC L2"],
    "small_business_status": True,
    "clearance_status": "none",
    "capabilities": ["cloud migration", "AWS GovCloud", "DevSecOps"],
}


async def run_one(slug: str, fixtures_dir: Path) -> dict:
    manifest = json.loads((fixtures_dir / slug / "manifest.json").read_text())
    pdf_path = (
        fixtures_dir / slug / "attachments" / manifest["attachments"][0]["filename"]
    )
    llm = LLM()

    parsed = await ParsePdfSkill().run(ParsePdfInput(path=str(pdf_path)))
    if parsed.unparseable:
        return {"unparseable": True, "package_sections_present": set()}

    reqs_out = await ExtractRequirementsSkill(llm).run(
        ExtractRequirementsInput(parsed_chunks=parsed.chunks)
    )
    score_out = await ScoreFitSkill(llm).run(
        ScoreFitInput(
            company_profile=DEMO_COMPANY,
            requirements=[r.model_dump() for r in reqs_out.requirements],
        )
    )
    risks_out = await DetectRisksSkill(llm).run(
        DetectRisksInput(
            company_profile=DEMO_COMPANY,
            requirements=[r.model_dump() for r in reqs_out.requirements],
            opportunity=manifest["opportunity"],
        )
    )

    mode = "reject_summary" if score_out.decision == "reject" else "full"
    pkg_out = await GenerateActionPackageSkill(llm).run(
        GenerateActionPackageInput(
            mode=mode,
            company_profile=DEMO_COMPANY,
            opportunity=manifest["opportunity"],
            requirements=[r.model_dump() for r in reqs_out.requirements],
            fit_score=score_out.model_dump(),
            risks=[r.model_dump() for r in risks_out.risks],
        )
    )

    sections: set[str] = set()
    if pkg_out.executive_summary:
        sections.add("executive_summary")
    if pkg_out.compliance_matrix:
        sections.add("compliance_matrix")
    if pkg_out.human_approval_required:
        sections.add("approval")

    return {
        "decision": score_out.decision,
        "total_score": score_out.total_score,
        "blockers": score_out.blockers,
        "requirement_count": len(reqs_out.requirements),
        "risk_count": len(risks_out.risks),
        "package_sections_present": sections,
    }


async def main() -> int:
    fixtures = Path("fixtures")
    failures = 0
    for slug in ["strong-pursue", "maybe", "reject", "adversarial-image-pdf"]:
        manifest = json.loads((fixtures / slug / "manifest.json").read_text())
        actual = await run_one(slug, fixtures)
        try:
            assert_fixture(slug, manifest, actual)
            print(f"✓ {slug}")
        except AssertionError as exc:
            print(f"✗ {slug}: {exc}")
            failures += 1
    return failures


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

- [ ] **Step 2: Assertions**

`eval/runner/assertions.py`:

```python
"""Eval assertions per PRD §19."""
from __future__ import annotations


def assert_fixture(slug: str, manifest: dict, actual: dict) -> None:
    expected_band = manifest["expected_decision_band"]
    if slug == "adversarial-image-pdf":
        assert actual.get("unparseable") is True, (
            "adversarial fixture must be marked unparseable"
        )
        return

    assert actual["decision"] == expected_band, (
        f"decision {actual['decision']} != expected {expected_band}"
    )

    if expected_band == "reject":
        assert actual["total_score"] == 0, (
            "reject fixture must score 0 (§11.1)"
        )
        for blocker in manifest.get("expected_critical_blockers", []):
            assert any(blocker.lower() in b.lower() for b in actual["blockers"]), (
                f"missing blocker: {blocker}"
            )
    else:
        assert actual["requirement_count"] >= 5, (
            f"only {actual['requirement_count']} requirements extracted"
        )

    assert "approval" in actual["package_sections_present"], (
        "human_approval_required must be present (§5.13)"
    )
```

- [ ] **Step 3: Makefile target**

```makefile
eval: ## Run the evaluation harness against seeded fixtures (PRD §19)
	uv run python -m eval.runner.run
```

- [ ] **Step 4: First run + capture goldens**

```bash
make eval
```

For each fixture's first successful run, save `actual` to `eval/goldens/<slug>.json` for future drift detection.

- [ ] **Step 5: Commit**

```bash
git add eval/ Makefile
git commit -m "feat(eval): A12 eval harness with §11.1 + §5.13 assertions"
```

---

# PHASE 6 — Product UI (`/web`)

Consumes the SSE stream + REST API. Replaces the marketing-only `/landing`. Built in dependency order: API client → profile/goal entry → timeline → cards → detail → action package → approval gate.

> **Pre-Phase-6 backend additions** (small endpoints that Phase 6 calls):
> - `GET /agent-runs/{id}/opportunities` — list opportunities for a run, with rolled-up fit/decision summaries
> - `GET /opportunities/{id}/pdf-url` — return a Supabase-Storage signed URL for the solicitation PDF

These are added in Task 6.0 below.

---

### Task 6.0: Backend endpoints required by `/web`

**Files:**
- Modify: `api/routes/agent_runs.py` — add `GET /{id}/opportunities`
- Modify: `api/routes/opportunities.py` — add `GET /{id}/pdf-url`
- Modify: `api/repositories/opportunity.py` — add `list_for_run` if missing

- [ ] **Step 1: Implement `GET /agent-runs/{id}/opportunities`**

Returns a flat list with `id, title, agency, due_date, naics, set_aside, fit_score, decision, top_reason, main_risk` per opportunity. Joins `opportunities` ⨝ `fit_scores` ⨝ first `risk_flags` row.

- [ ] **Step 2: Implement `GET /opportunities/{id}/pdf-url`**

Calls `storage.create_signed_url(opportunity.attachment_path, expires_in=300)` and returns `{"url": "...", "expires_in": 300}`.

- [ ] **Step 3: Tests for both**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(api): GET /agent-runs/{id}/opportunities + /opportunities/{id}/pdf-url"
```

---

### Task 6.1: B2 — API client + zod codegen from /schemas

**Files:**
- Create: `web/src/lib/api.ts`
- Create: `web/src/lib/schemas/` — codegen target (zod)
- Create: `web/scripts/codegen.mjs`

- [ ] **Step 1: Codegen script**

`web/scripts/codegen.mjs`:

```javascript
import { jsonSchemaToZod } from "json-schema-to-zod";
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const schemasDir = "../schemas";
const outDir = "src/lib/schemas";
mkdirSync(outDir, { recursive: true });

for (const f of readdirSync(schemasDir).filter(f => f.endsWith(".schema.json"))) {
  const schema = JSON.parse(readFileSync(join(schemasDir, f), "utf8"));
  const code = jsonSchemaToZod(schema, { module: "esm" });
  const name = f.replace(".schema.json", "").replace(/-/g, "_");
  writeFileSync(join(outDir, `${name}.ts`), code);
  console.log(`✓ ${name}.ts`);
}
```

- [ ] **Step 2: API client**

`web/src/lib/api.ts`:

```typescript
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  createProfile: (body: unknown) =>
    request("/company-profiles", { method: "POST", body: JSON.stringify(body) }),
  getProfile: (id: string) => request(`/company-profiles/${id}`),
  createRun: (body: unknown) =>
    request("/agent-runs", { method: "POST", body: JSON.stringify(body) }),
  getRun: (id: string) => request(`/agent-runs/${id}`),
  getRunOpportunities: (id: string) => request(`/agent-runs/${id}/opportunities`),
  getOpportunity: (id: string) => request(`/opportunities/${id}`),
  getRequirements: (id: string) => request(`/opportunities/${id}/requirements`),
  getFitScore: (id: string) => request(`/opportunities/${id}/fit-score`),
  getRisks: (id: string) => request(`/opportunities/${id}/risks`),
  getActionPackage: (id: string) => request(`/action-packages/${id}`),
  getPdfUrl: (id: string) => request<{ url: string }>(`/opportunities/${id}/pdf-url`),
  resumeRun: (id: string, answer: unknown) =>
    request(`/agent-runs/${id}/resume`, {
      method: "POST",
      body: JSON.stringify({ answer }),
    }),
};
```

- [ ] **Step 3: Run codegen, commit**

```bash
cd web && npm install && npm run codegen
git add web/scripts/ web/src/lib/ web/package.json web/package-lock.json
git commit -m "feat(web): B2 API client + zod-codegen from /schemas"
```

---

### Tasks 6.2–6.13: Profile form, goal entry, SSE hook, timeline, cards, detail, action package

Each follows the same pattern: small focused component → page composing them → smoke test in browser → commit.

The detailed code blocks for each component are in **Part 1 §"Phase 6"** of the original plan; with the codegen and API client established in Task 6.1 above, the remaining components are mechanical: copy the JSX patterns, wire state with `useState`/`use`/`useTraceStream`, style with Tailwind 4.

Component map:
- **Task 6.2** — `ProfileForm.tsx` + `app/profile/page.tsx`
- **Task 6.3** — `app/runs/new/page.tsx`
- **Task 6.4** — `lib/useTraceStream.ts` (typed `TraceEvent` discriminated union — must include `subagent_spawned` / `subagent_completed` from Task 4.2)
- **Task 6.5** — `components/RunTimeline.tsx` + `app/runs/[id]/page.tsx`
- **Task 6.6** — `components/OpportunityCard.tsx` + `components/RankedList.tsx`
- **Task 6.7** — `app/opportunities/[id]/page.tsx`
- **Task 6.8** — `components/RequirementsList.tsx` + `components/PdfDeepLink.tsx`
- **Task 6.9** — `components/ScoreBreakdown.tsx`
- **Task 6.10** — `app/action-packages/[id]/page.tsx` + `components/ApprovalGate.tsx` + `components/ExecutiveBrief.tsx`
- **Task 6.11** — `components/ComplianceMatrix.tsx` + `components/RiskRegister.tsx`
- **Task 6.12** — `components/ProposalChecklist.tsx` + `components/ActionTimeline.tsx` + `components/PartnerSuggestions.tsx`
- **Task 6.13** — `components/OutreachDraft.tsx`

Test plan: after each task, smoke-test in browser:
```bash
make dev          # backend on :8000
npm -w web run dev  # frontend on :3001
# Walk: /profile → /runs/new → /runs/{id} → /opportunities/{id} → /action-packages/{id}
```

Commit boundary per task. All commits prefixed `feat(web):`.

---

# PHASE 7 — Production Hardening

---

### Task 7.1: Repository transaction boundaries

Multi-step writes (skill writing N requirements + 1 fit_score + N risks) currently auto-commit per call. A failure midway leaves partial data.

**Files:**
- Modify: `api/repositories/*.py` — drop auto-commits
- Modify: `api/deps.py` — middleware that commits on 2xx response

- [ ] **Step 1: Audit repo create/update methods for `await self._session.commit()`**

```bash
grep -rn "await self._session.commit()" api/repositories/
```

For each occurrence: remove the commit, leave the flush + refresh.

- [ ] **Step 2: Add commit-on-success middleware**

In `api/deps.py`, the `get_session` dependency should commit on a clean exit:

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 3: Audit existing tests for implicit-commit reliance**

```bash
uv run pytest -v
```

Fix any failures.

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor(repo): move commit boundaries to session middleware"
```

---

### Task 7.2: Anthropic retry/backoff

**Files:**
- Modify: `api/llm.py` — wrap `messages.create` with exponential backoff
- Modify: `pyproject.toml` — add `tenacity>=9.0`

- [ ] **Step 1: Add dep**

```toml
"tenacity>=9.0",
```

- [ ] **Step 2: Decorate**

```python
import anthropic
from tenacity import (
    retry, retry_if_exception_type, stop_after_attempt, wait_exponential,
)

@retry(
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIError)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    reraise=True,
)
async def _call_with_retry(self, **kwargs):
    return await self._client.messages.create(**kwargs)
```

- [ ] **Step 3: Test (mock raising RateLimitError twice then succeeding)**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(llm): exponential backoff retry on Anthropic 429/5xx (4 attempts)"
```

---

### Task 7.3: Structured logging

**Files:**
- Modify: `api/main.py` — configure `structlog`
- Modify: `pyproject.toml` — add `structlog>=24`

- [ ] **Step 1: Wire structlog**

```python
import logging
import sys

import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
)
log = structlog.get_logger()
```

- [ ] **Step 2: Replace ad-hoc logging.info calls in skills + bridge**

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(logging): structlog with JSON renderer + contextvars"
```

---

### Task 7.4: Run budget enforcement (already partial in Task 4.1)

`hermes_runner` already wraps `proc` in `asyncio.wait_for(timeout=settings.run_budget_seconds)` and emits `run_completed/partial` on timeout. Add cumulative cost tracking.

**Files:**
- Modify: `api/agent/hermes_runner.py`

- [ ] **Step 1: Track cumulative cost**

In the bridge loop, accumulate `cost_usd` from `tool_returned` events. If it crosses `settings.run_budget_usd`, kill the subprocess and emit `run_completed/partial`.

- [ ] **Step 2: Test**

```bash
uv run pytest api/tests/test_hermes_runner.py -v -k "budget"
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(agent): cost-budget enforcement in hermes_runner"
```

---

### Task 7.5: §11.1 post-run audit (defense-in-depth)

The §11.1 helper is enforced inside `score_fit`. Add a final gate in the runner: before persisting any `action_package` with `decision != reject`, re-check that none of the persisted requirements are eligibility blockers.

**Files:**
- Modify: `api/agent/hermes_runner.py`

- [ ] **Step 1: Audit function**

```python
from api.policy.eligibility import check_eligibility_short_circuit

async def _audit_eligibility(run_id, opp_repo, action_pkg):
    if action_pkg.decision == "reject":
        return
    requirements = await opp_repo.list_requirements(action_pkg.opportunity_id)
    blockers = check_eligibility_short_circuit(
        profile=action_pkg.company_profile,
        requirements=[r.model_dump() for r in requirements],
    )
    if blockers:
        log.error("eligibility_audit_override",
                  blockers=blockers, run_id=run_id)
        action_pkg.decision = "reject"
        action_pkg.executive_summary = (
            f"OVERRIDE: §11.1 audit found eligibility blockers: {blockers}"
        )
```

Single source of truth — uses the same helper as `score_fit`.

- [ ] **Step 2: Eval-harness assertion catches regressions**

The reject fixture's golden already asserts this. Verify `make eval` passes.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(agent): post-run §11.1 audit override (defense-in-depth)"
```

---

### Task 7.6: SAM.gov fallback chain (live → cached → seeded)

PRD §5.4. The cache layer.

**Files:**
- Create: Migration `0004_sam_cache.py`
- Modify: `api/skills/search_sam/skill.py` — wrap with cache lookup

- [ ] **Step 1: Cache table migration**

```python
def upgrade() -> None:
    op.create_table(
        "sam_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("query_key", sa.String, unique=True, index=True, nullable=False),
        sa.Column("results", postgresql.JSONB, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
```

- [ ] **Step 2: Skill logic**

```
1. Compute query_key from input params (sorted, deterministic).
2. If cache hit and fetched_at < 24h ago: return cached, NOT degraded.
3. Else call live SAM.
4. On success: write to cache.
5. On 429/5xx: return cache if any (not degraded, age noted), else degraded=True with empty results.
```

- [ ] **Step 3: Tests for hit / miss / stale-cache-on-error**

- [ ] **Step 4: Commit**

```bash
make migrate
git commit -m "feat(skills): SAM cache layer (live → cached → seeded fallback)"
```

---

### Task 7.7: Delete the replayer

Phase 4 has been green for at least one full pass.

**Files:**
- Delete: `api/agent/replay.py`
- Modify: `api/routes/agent_runs.py` — drop `USE_REPLAYER` branch
- Modify: `api/config.py` — remove `use_replayer` field
- Modify: `api/tests/test_routes.py` — drop replayer-specific assertions

- [ ] **Step 1: Delete**

```bash
git rm api/agent/replay.py
```

- [ ] **Step 2: Drop the branch**

In `api/routes/agent_runs.py`, replace the `if settings.use_replayer:` block with the single `run_capture` call.

- [ ] **Step 3: Run full suite**

```bash
uv run pytest -v
```

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(agent): delete pre-A9 replayer; hermes_runner is the only path"
```

---

# Self-Review

**Spec coverage check** (PRD §5 features, §4.5 agent architecture, §10 output schemas, §11.1 eligibility, §13.1 demo, §19 eval, §7 stack):

- ✓ §5.1 Profile input — Phase 0 (POST already exists per A3) + Phase 6 form
- ✓ §5.2 Goal input — Phase 6 Task 6.3
- ✓ §5.3 Run timeline — Phase 6 Task 6.5
- ✓ §5.4 Opportunity loader — Task 1.5 (load_seeded), Task 3.1 (search_sam), Task 7.6 (cache)
- ✓ §5.5 Document parsing — already done (parse_pdf A4)
- ✓ §5.6 Requirement extraction — already done (extract_requirements A5)
- ✓ §5.7 Fit scoring — Tasks 2.0, 2.1, 2.2
- ✓ §5.8 Risk detection — Tasks 2.3, 2.4
- ✓ §5.9 Ranking — Task 3.4 + Task 6.6
- ✓ §5.10 Detail view — Tasks 6.7-6.9
- ✓ §5.11 Action package — Tasks 2.5, 2.6 + Tasks 6.10-6.13
- ✓ §5.12 Partner suggestion — included in action package full mode
- ✓ §5.13 Approval gate — Task 6.10 + DEFAULT_APPROVAL forcing in skill
- ✓ §4.5 Planner loop — Task 4.1 (hermes_runner subprocess)
- ✓ §4.5 Tool registry — Task 4.1 (skill_registry + tool_callback)
- ✓ §4.5 Decision policy / error recovery — Task 7.4 (budget) + 7.6 (SAM fallback) + 4.5 (human review)
- ✓ §4.5 Observability — Task 4.2 (bridge) + Task 7.3 (structured logs)
- ✓ §10 Structured outputs — all schemas codegen via Task 6.1
- ✓ §11.1 Eligibility conservatism — shared helper Task 2.0; used Task 2.2 (skill) + Task 5.1 (eval) + Task 7.5 (audit)
- ✓ §13.1 Demo script — Phases 1, 4, 6 enable
- ✓ §19 Eval harness — Phase 5
- ✓ §7.1 Frontend — Phase 6
- ✓ §7.2 Backend — Phases 0, 2, 3, 4, 7
- ✓ §7.3 Agent layer — Phase 4
- ✓ §7.5 Storage — already wired (api/storage.py per inherited state)
- ✓ §7.6 Deploy — already done in repo

**Type consistency:**
- `LLM` (class) and `complete_structured` (method) used uniformly across every Phase 2/3 skill code block.
- `pydantic.BaseModel` used uniformly for skill I/O — matches existing `parse_pdf` and `extract_requirements`.
- `ScoreFitOutput.decision` is `Literal["strong_pursue", "pursue", "maybe", "reject"]` — same enum used by eval assertions and frontend `OpportunityCard`.
- `RiskFlag.severity` is `Literal["critical_blocker", "major_risk", "moderate_risk", "minor_concern"]` — same in skill + frontend.
- `mode: Literal["full", "reject_summary"]` consistent in skill + Hermes manifest references.
- `TraceEvent` union in Task 6.4 covers all 8 base + 2 subagent types (added in Task 4.2).
- Component named `RunTimeline.tsx` (Task 6.5) for the run timeline; `ActionTimeline.tsx` (Task 6.12) for the action-package timeline. No name collision.

**Critical-path tasks** (block downstream work):
- Task 4.0 (Hermes protocol capture) — blocks Tasks 4.1-4.4
- Tasks 1.1-1.4 (fixtures) — block eval harness, demo, and 2 skipped parse_pdf tests
- Task 2.0 (eligibility helper) — blocks Task 2.2 and Task 7.5
- Task 6.0 (backend endpoints for /web) — blocks Task 6.6 (RankedList) and 6.8 (PdfDeepLink)

**Estimated runway:** 19-24 working days for one engineer; 11-14 if Track A (Phases 0, 2, 3, 4, 5, 7) and Track B (Phases 0/Web, 6) run parallel after Phase 0.

---

End of Part 2.
