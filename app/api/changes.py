"""Change requests API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    log_artefact_activity,
    log_document_workflow_activity_from_patch,
    should_log_generic_document_update,
    updated_summary,
)
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_role
from app.models import ChangeRequest, Project
from app.models.user import User, UserRole
from app.schemas import (
    ChangeRequestCreate,
    ChangeRequestResponse,
    ChangeRequestUpdate,
    PaginatedResponse,
)

router = APIRouter()


def _change_response(item: ChangeRequest) -> ChangeRequestResponse:
    return ChangeRequestResponse.model_validate(item)


@router.get("", response_model=PaginatedResponse[ChangeRequestResponse])
async def list_change_requests(
    project_id: int = Query(..., description="Filter by project ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    base = select(ChangeRequest).where(ChangeRequest.project_id == project_id)
    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = base.order_by(ChangeRequest.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = [_change_response(item) for item in result.scalars().all()]
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=ChangeRequestResponse, status_code=201)
async def create_change_request(
    data: ChangeRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    project = (
        await db.execute(select(Project).where(Project.id == data.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    change_id = await next_doc_id(
        db, ChangeRequest, ChangeRequest.change_id, data.project_id, project.prefix, "CHG"
    )

    existing = await db.execute(
        select(ChangeRequest).where(
            ChangeRequest.project_id == data.project_id,
            ChangeRequest.change_id == change_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Change request with this ID already exists")

    item = ChangeRequest(
        project_id=data.project_id,
        change_id=change_id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        change_type=data.change_type,
        impact_assessment=data.impact_assessment,
        justification=data.justification,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await log_artefact_activity(
        db,
        "change",
        item.id,
        "created",
        f"{current_user.full_name} created change request {item.change_id}",
    )
    return _change_response(item)


@router.get("/{change_id}", response_model=ChangeRequestResponse)
async def get_change_request(
    change_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    item = (
        await db.execute(select(ChangeRequest).where(ChangeRequest.id == change_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Change request not found")
    return _change_response(item)


@router.patch("/{change_id}", response_model=ChangeRequestResponse)
async def update_change_request(
    change_id: int,
    data: ChangeRequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (
        await db.execute(select(ChangeRequest).where(ChangeRequest.id == change_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Change request not found")

    fields_set = data.model_fields_set
    previous_status = item.status if "status" in fields_set else None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    await log_document_workflow_activity_from_patch(
        db,
        artefact_type="change",
        artefact_id=item.id,
        public_id=item.change_id,
        actor=current_user,
        fields_set=fields_set,
        previous_status=previous_status,
        next_status=item.status,
    )
    if should_log_generic_document_update(fields_set):
        await log_artefact_activity(
            db,
            "change",
            item.id,
            "updated",
            updated_summary(current_user.full_name, "change request", item.change_id, fields_set),
        )
    return _change_response(item)


@router.delete("/{change_id}", status_code=204)
async def delete_change_request(
    change_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (
        await db.execute(select(ChangeRequest).where(ChangeRequest.id == change_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Change request not found")
    await log_artefact_activity(
        db,
        "change",
        item.id,
        "deleted",
        f"{current_user.full_name} deleted change request {item.change_id}",
    )
    await db.delete(item)
