"""Project parameters and variables API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_project_access, require_role
from app.models import Project, ProjectVariable
from app.models.user import User, UserRole
from app.schemas import (
    ProjectVariableCreate,
    ProjectVariableResponse,
    ProjectVariableUpdate,
)

router = APIRouter()


@router.get("", response_model=list[ProjectVariableResponse])
async def list_project_variables(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await require_project_access(db, current_user, project_id)

    result = await db.execute(
        select(ProjectVariable)
        .where(ProjectVariable.project_id == project_id)
        .order_by(ProjectVariable.kind.asc(), ProjectVariable.key.asc())
    )
    return result.scalars().all()


@router.post("", response_model=ProjectVariableResponse, status_code=201)
async def create_project_variable(
    data: ProjectVariableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    project = (
        await db.execute(select(Project).where(Project.id == data.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await require_project_access(
        db,
        current_user,
        data.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    existing = (
        await db.execute(
            select(ProjectVariable).where(
                ProjectVariable.project_id == data.project_id,
                ProjectVariable.kind == data.kind,
                ProjectVariable.key == data.key,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Variable key already exists in this project")

    item = ProjectVariable(
        project_id=data.project_id,
        kind=data.kind,
        key=data.key,
        value=data.value,
        description=data.description,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=ProjectVariableResponse)
async def update_project_variable(
    item_id: int,
    data: ProjectVariableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (
        await db.execute(select(ProjectVariable).where(ProjectVariable.id == item_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Variable not found")

    await require_project_access(
        db,
        current_user,
        item.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    updated_kind = data.kind if data.kind is not None else item.kind
    updated_key = data.key if data.key is not None else item.key

    existing = (
        await db.execute(
            select(ProjectVariable).where(
                ProjectVariable.project_id == item.project_id,
                ProjectVariable.kind == updated_kind,
                ProjectVariable.key == updated_key,
                ProjectVariable.id != item_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Variable key already exists in this project")

    fields_set = data.model_fields_set
    if "kind" in fields_set and data.kind is not None:
        item.kind = data.kind
    if "key" in fields_set and data.key is not None:
        item.key = data.key
    if "value" in fields_set and data.value is not None:
        item.value = data.value
    if "description" in fields_set:
        item.description = data.description

    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_project_variable(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (
        await db.execute(select(ProjectVariable).where(ProjectVariable.id == item_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Variable not found")
    await require_project_access(
        db,
        current_user,
        item.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )
    await db.delete(item)
