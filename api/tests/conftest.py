"""Shared test fixtures.

Provides a minimal in-memory FakeSupabase that mimics enough of supabase-py's
AsyncClient for our route tests. Real Supabase integration tests live in a
separate suite (TBD) that requires SUPABASE_URL credentials.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
import pytest_asyncio

TEST_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
TEST_INTERNAL_API_KEY = "test-internal-key"


class _Resp:
    def __init__(self, data: Any) -> None:
        self.data = data


class _Query:
    def __init__(self, store: dict[str, dict[str, dict[str, Any]]], table: str) -> None:
        self._store = store
        self._table = table
        self._kind: str = "select"
        self._payload: Any = None
        self._filters: list[tuple[str, str, Any]] = []
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._maybe_single = False

    # ---- builders -----------------------------------------------------------
    def select(self, _cols: str = "*") -> "_Query":
        self._kind = "select"
        return self

    def insert(self, payload: dict[str, Any] | list[dict[str, Any]]) -> "_Query":
        self._kind = "insert"
        self._payload = payload
        return self

    def update(self, payload: dict[str, Any]) -> "_Query":
        self._kind = "update"
        self._payload = payload
        return self

    def delete(self) -> "_Query":
        self._kind = "delete"
        return self

    def eq(self, col: str, value: Any) -> "_Query":
        self._filters.append((col, "eq", value))
        return self

    def in_(self, col: str, values: list[Any]) -> "_Query":
        self._filters.append((col, "in", values))
        return self

    def is_(self, col: str, value: str) -> "_Query":
        self._filters.append((col, "is", value))
        return self

    def order(self, col: str, *, desc: bool = False) -> "_Query":
        self._order = (col, desc)
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    def maybe_single(self) -> "_Query":
        self._maybe_single = True
        return self

    def single(self) -> "_Query":
        self._maybe_single = False
        return self

    # ---- execution ----------------------------------------------------------
    def _matches(self, row: dict[str, Any]) -> bool:
        for col, op, value in self._filters:
            row_value = row.get(col)
            if op == "eq" and (row_value is None or str(row_value) != str(value)):
                return False
            if op == "in" and str(row_value) not in {str(v) for v in value}:
                return False
            if op == "is" and value == "null" and row_value is not None:
                return False
        return True

    async def execute(self) -> _Resp:
        rows_dict = self._store.setdefault(self._table, {})
        if self._kind == "select":
            rows = [r for r in rows_dict.values() if self._matches(r)]
            if self._order is not None:
                col, desc = self._order
                rows.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
            if self._limit is not None:
                rows = rows[: self._limit]
            if self._maybe_single:
                return _Resp(rows[0] if rows else None)
            return _Resp(rows)
        if self._kind == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted: list[dict[str, Any]] = []
            now = datetime.now(timezone.utc).isoformat()
            for p in payloads:
                row = dict(_TABLE_DEFAULTS.get(self._table, {}))
                row.update(p)
                row.setdefault("id", str(uuid.uuid4()))
                row.setdefault("created_at", now)
                if self._table in _TABLES_WITH_UPDATED_AT:
                    row.setdefault("updated_at", now)
                if self._table == "waitlist_signups":
                    row["email"] = str(row["email"]).strip().lower()
                rows_dict[row["id"]] = row
                inserted.append(row)
            return _Resp(inserted)
        if self._kind == "update":
            updated: list[dict[str, Any]] = []
            for row in rows_dict.values():
                if self._matches(row):
                    row.update(self._payload)
                    updated.append(row)
            return _Resp(updated)
        if self._kind == "delete":
            removed: list[dict[str, Any]] = []
            for key, row in list(rows_dict.items()):
                if self._matches(row):
                    removed.append(rows_dict.pop(key))
            return _Resp(removed)
        raise RuntimeError(f"Unknown kind: {self._kind}")


# Tables whose schema has `updated_at` (mimics ON UPDATE CURRENT_TIMESTAMP).
# Other tables only have `created_at`.
_TABLES_WITH_UPDATED_AT: frozenset[str] = frozenset(
    {"profiles", "company_profiles", "opportunities", "waitlist_signups"}
)


# Per-table defaults that mimic the Supabase Postgres `DEFAULT` clauses on the
# real schema. Any field not provided on insert falls back to these. Keeps
# FakeSupabase self-contained without requiring tests to know every column.
_TABLE_DEFAULTS: dict[str, dict[str, Any]] = {
    "company_profiles": {
        "owner_profile_id": str(TEST_USER_ID),
        "website": None,
        "description": None,
        "capabilities": [],
        "industry_keywords": [],
        "location": None,
        "service_area": [],
        "naics_codes": [],
        "certifications": [],
        "small_business_status": False,
        "sam_status": None,
        "clearance_status": None,
        "past_performance": [],
        "insurance_bonding_status": None,
        "preferred_contract_size": None,
        "preferred_role": "either",
    },
    "opportunities": {
        "slug": "",
        "source": "sam.gov",
        "active": True,
        "resource_links": [],
        "opportunity_status": "open",
        "attachments": [],
        "raw_payload": None,
        "notice_type": None,
        "posted_date": None,
        "office_name": None,
        "psc_code": None,
        "record_kind": None,
        "source_url": None,
        "due_date": None,
        "naics": None,
        "set_aside": None,
        "place_of_performance": None,
        "description": None,
        "source_notice_id": None,
    },
    "agent_runs": {
        "profile_id": str(TEST_USER_ID),
        "steps": [],
        "opportunities": [],
        "status": "pending",
        "selected_opportunity_id": None,
        "action_package_id": None,
        "completed_at": None,
    },
    "extracted_requirements": {
        "value": None,
        "description": None,
        "evidence_snippet": None,
        "source_document": None,
        "page_number": None,
        "is_blocker": False,
    },
    "fit_scores": {
        "breakdown": {},
        "strengths": [],
        "weaknesses": [],
        "blockers": [],
        "missing_info": [],
        "recommended_next_action": None,
    },
    "risk_flags": {
        "evidence": None,
        "mitigation": None,
        "requires_human_review": False,
    },
    "action_packages": {
        "compliance_matrix": [],
        "risk_register": [],
        "proposal_checklist": [],
        "timeline": [],
        "partner_suggestions": [],
        "outreach_draft": None,
        "approval_required": ["Human approval required before execution"],
    },
    "profiles": {
        "email": "tester@example.com",
        "full_name": None,
        "company_name": None,
        "role": "owner",
    },
    "waitlist_signups": {
        "company": None,
        "role": None,
        "source": "landing",
    },
    "api_keys": {
        "scopes": ["tools:*"],
        "last_used_at": None,
        "revoked_at": None,
    },
}


class FakeSupabase:
    """In-memory PostgREST-like client. One per test."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, dict[str, Any]]] = {}

    def table(self, name: str) -> _Query:
        return _Query(self._store, name)

    def from_(self, name: str) -> _Query:  # alias
        return self.table(name)


@pytest.fixture
def fake_supabase() -> FakeSupabase:
    return FakeSupabase()


@pytest_asyncio.fixture
async def client(fake_supabase: FakeSupabase):
    """ASGI client with Supabase dependency overridden to FakeSupabase."""
    import httpx
    from httpx import ASGITransport

    from api.auth import AuthenticatedUser, require_user
    from api.config import settings
    from api.db import get_client
    from api.deps import get_supabase
    from api.main import app

    async def _fake_dep() -> FakeSupabase:
        return fake_supabase

    async def _fake_user() -> AuthenticatedUser:
        return AuthenticatedUser(id=TEST_USER_ID, email="tester@example.com")

    settings.internal_api_key = TEST_INTERNAL_API_KEY
    app.dependency_overrides[get_supabase] = _fake_dep
    app.dependency_overrides[get_client] = _fake_dep
    app.dependency_overrides[require_user] = _fake_user
    transport = ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_supabase, None)
        app.dependency_overrides.pop(get_client, None)
        app.dependency_overrides.pop(require_user, None)
