from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.auth import AuthenticatedUser, require_user
from api.deps import (
    get_agent_run_repo,
    get_company_profile_repo,
    get_opportunity_repo,
)
from api.redis import redis_client
from api.repositories.agent_run import AgentRunRepository
from api.repositories.company_profile import CompanyProfileRepository
from api.repositories.opportunity import OpportunityRepository
from api.schemas.agent_run import AgentRun
from api.schemas.agent_run_create import AgentRunCreate
from api.schemas.opportunity import Opportunity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


@router.post("", response_model=AgentRun, status_code=201)
async def create_agent_run(
    payload: AgentRunCreate,
    user: AuthenticatedUser = Depends(require_user),
    run_repo: AgentRunRepository = Depends(get_agent_run_repo),
    profile_repo: CompanyProfileRepository = Depends(get_company_profile_repo),
) -> AgentRun:
    profile_id: uuid.UUID | None = payload.profile_id
    if profile_id is None and payload.profile is not None:
        data = payload.profile.model_dump(exclude_none=True)
        data["owner_profile_id"] = str(user.id)
        created = await profile_repo.create(data)
        profile_id = uuid.UUID(created["id"])
    elif profile_id is not None:
        existing = await profile_repo.get_owned(profile_id, user.id)
        if existing is None:
            raise HTTPException(400, f"profile_id {profile_id} not found")

    row = await run_repo.create(
        goal=payload.goal,
        profile_id=user.id,
        company_profile_id=profile_id,
    )

    return AgentRun.model_validate(row)


@router.get("/{run_id}", response_model=AgentRun)
async def get_agent_run(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    repo: AgentRunRepository = Depends(get_agent_run_repo),
) -> AgentRun:
    row = await repo.get_owned(run_id, user.id)
    if row is None:
        raise HTTPException(404, "Agent run not found")
    return AgentRun.model_validate(row)


@router.get(
    "/{run_id}/opportunities",
    response_model=list[Opportunity],
)
async def list_run_opportunities(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    run_repo: AgentRunRepository = Depends(get_agent_run_repo),
    opp_repo: OpportunityRepository = Depends(get_opportunity_repo),
) -> list[Opportunity]:
    run = await run_repo.get_owned(run_id, user.id)
    if run is None:
        raise HTTPException(404, "Agent run not found")
    ids = [uuid.UUID(s) for s in (run.get("opportunities") or [])]
    rows = await opp_repo.list_by_ids(ids)
    return [Opportunity.model_validate(r) for r in rows]


@router.get("/{run_id}/stream")
async def stream_agent_run(
    run_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    repo: AgentRunRepository = Depends(get_agent_run_repo),
) -> StreamingResponse:
    """SSE forwarder. Subscribes to `agent-run:{run_id}` and yields events.

    Sends `:keepalive\\n\\n` every 15s of silence so proxies (nginx) don't drop the
    connection. Closes cleanly on `run_completed`.
    """
    run = await repo.get_owned(run_id, user.id)
    if run is None:
        raise HTTPException(404, "Agent run not found")

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"agent-run:{run_id}")

    async def event_gen():
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ":keepalive\n\n"
                    continue

                if msg is None:
                    continue
                if msg.get("type") != "message":
                    continue

                data = msg["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("dropping malformed pubsub payload: %r", data)
                    continue

                event_type = event.get("type", "message")
                yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"

                if event_type == "run_completed":
                    break
        finally:
            await pubsub.unsubscribe(f"agent-run:{run_id}")
            await pubsub.aclose()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
