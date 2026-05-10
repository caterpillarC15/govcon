from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.auth import AuthenticatedUser, InternalActor, require_internal_actor, require_user
from api.deps import get_action_package_repo
from api.repositories.action_package import ActionPackageRepository
from api.schemas.action_package import ActionPackage
from api.schemas.action_package_create import ActionPackageCreate

router = APIRouter(prefix="/action-packages", tags=["action-packages"])


@router.get("/{package_id}", response_model=ActionPackage)
async def get_action_package(
    package_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_user),
    repo: ActionPackageRepository = Depends(get_action_package_repo),
) -> ActionPackage:
    row = await repo.get_owned(package_id, user.id)
    if row is None:
        raise HTTPException(404, "Action package not found")
    return ActionPackage.model_validate(row)


@router.post("", response_model=ActionPackage, status_code=201)
async def create_action_package(
    payload: ActionPackageCreate,
    _actor: InternalActor = Depends(require_internal_actor),
    repo: ActionPackageRepository = Depends(get_action_package_repo),
) -> ActionPackage:
    row = await repo.create(payload.model_dump())
    return ActionPackage.model_validate(row)
