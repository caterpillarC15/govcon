from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import AuthenticatedUser, require_user
from api.deps import get_profile_repo
from api.repositories.profile import ProfileRepository
from api.schemas.profile import Profile, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=Profile)
async def get_my_profile(
    user: AuthenticatedUser = Depends(require_user),
    repo: ProfileRepository = Depends(get_profile_repo),
) -> Profile:
    row = await repo.upsert_user_profile(profile_id=user.id, email=user.email)
    return Profile.model_validate(row)


@router.post("/me", response_model=Profile)
async def update_my_profile(
    payload: ProfileUpdate,
    user: AuthenticatedUser = Depends(require_user),
    repo: ProfileRepository = Depends(get_profile_repo),
) -> Profile:
    row = await repo.upsert_user_profile(
        profile_id=user.id,
        email=user.email,
        full_name=payload.full_name,
        company_name=payload.company_name,
    )
    return Profile.model_validate(row)
