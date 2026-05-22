"""Design items API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    log_artefact_activity,
    log_document_workflow_activity_from_patch,
    should_log_generic_document_update,
)
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_role
from app.models import DesignItem, Project
from app.models.user import User, UserRole
from app.schemas import DesignItemCreate, DesignItemResponse, DesignItemUpdate, PaginatedResponse

router = APIRouter()


def _design_response(item: DesignItem) -> DesignItemResponse:
    return DesignItemResponse.model_validate(item)


@router.get("", response_model=PaginatedResponse[DesignItemResponse])
async def list_design_items(
    project_id: int = Query(..., description="Filter by project ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    base = select(DesignItem).where(DesignItem.project_id == project_id)
    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = base.order_by(DesignItem.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = [_design_response(item) for item in result.scalars().all()]
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=DesignItemResponse, status_code=201)
async def create_design_item(
    data: DesignItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    project = (
        await db.execute(select(Project).where(Project.id == data.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    design_id = await next_doc_id(
        db, DesignItem, DesignItem.design_id, data.project_id, project.prefix, "DES"
    )

    existing = await db.execute(
        select(DesignItem).where(
            DesignItem.project_id == data.project_id,
            DesignItem.design_id == design_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Design item with this ID already exists")

    item = DesignItem(
        project_id=data.project_id,
        design_id=design_id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        design_type=data.design_type,
        linked_requirement_id=None,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await log_artefact_activity(
        db,
        "design",
        item.id,
        "created",
        f"{current_user.full_name} created design item {item.design_id}",
    )
    return _design_response(item)


@router.get("/{design_id}", response_model=DesignItemResponse)
async def get_design_item(
    design_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    item = (
        await db.execute(select(DesignItem).where(DesignItem.id == design_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Design item not found")
    return _design_response(item)


@router.patch("/{design_id}", response_model=DesignItemResponse)
async def update_design_item(
    design_id: int,
    data: DesignItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (
        await db.execute(select(DesignItem).where(DesignItem.id == design_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Design item not found")

    fields_set = data.model_fields_set
    previous_status = item.status if "status" in fields_set else None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    await log_document_workflow_activity_from_patch(
        db,
        artefact_type="design",
        artefact_id=item.id,
        public_id=item.design_id,
        actor=current_user,
        fields_set=fields_set,
        previous_status=previous_status,
        next_status=item.status,
    )
    if should_log_generic_document_update(fields_set):
        await log_artefact_activity(
            db,
            "design",
            item.id,
            "updated",
            f"{current_user.full_name} updated design item {item.design_id}",
        )
    return _design_response(item)


@router.delete("/{design_id}", status_code=204)
async def delete_design_item(
    design_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (
        await db.execute(select(DesignItem).where(DesignItem.id == design_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Design item not found")
    await log_artefact_activity(
        db,
        "design",
        item.id,
        "deleted",
        f"{current_user.full_name} deleted design item {item.design_id}",
    )
    await db.delete(item)
