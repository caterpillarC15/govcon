from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_waitlist_repo
from api.repositories.waitlist import WaitlistRepository
from api.schemas.waitlist import WaitlistSignupCreate, WaitlistSignupResponse

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


@router.post("", response_model=WaitlistSignupResponse)
async def join_waitlist(
    payload: WaitlistSignupCreate,
    repo: WaitlistRepository = Depends(get_waitlist_repo),
) -> WaitlistSignupResponse:
    _, already_registered = await repo.create_or_get(payload.model_dump(exclude_none=True))
    return WaitlistSignupResponse(already_registered=already_registered)
