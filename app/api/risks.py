"""Risk items API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import log_artefact_activity
from app.core.database import get_db
from app.core.id_generator import normalize_doc_id
from app.core.security import get_current_user, require_role
from app.models import Project, RiskItem
from app.models.user import User, UserRole
from app.schemas import RiskItemCreate, RiskItemResponse, RiskItemUpdate

router = APIRouter()


def _risk_response(item: RiskItem) -> RiskItemResponse:
    return RiskItemResponse.model_validate(item)


@router.get("", response_model=list[RiskItemResponse])
async def list_risk_items(
    project_id: int = Query(..., description="Filter by project ID"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RiskItem)
        .where(RiskItem.project_id == project_id)
        .order_by(RiskItem.created_at.desc())
    )
    return [_risk_response(item) for item in result.scalars().all()]


@router.post("", response_model=RiskItemResponse, status_code=201)
async def create_risk_item(
    data: RiskItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    project = (
        await db.execute(select(Project).where(Project.id == data.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        risk_id = normalize_doc_id(
            data.risk_id,
            expected_type_code="RSK",
            expected_project_prefix=project.prefix,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = await db.execute(
        select(RiskItem).where(
            RiskItem.project_id == data.project_id,
            RiskItem.risk_id == risk_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Risk item with this ID already exists")

    item = RiskItem(
        project_id=data.project_id,
        risk_id=risk_id,
        title=data.title,
        description=data.description,
        status=data.status,
        severity=data.severity,
        probability=data.probability,
        mitigation=data.mitigation,
        risk_category=data.risk_category,
        linked_requirement_id=data.linked_requirement_id,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await log_artefact_activity(
        db,
        "risk",
        item.id,
        "created",
        f"{current_user.full_name} created risk {item.risk_id}",
    )
    return _risk_response(item)


@router.get("/{risk_id}", response_model=RiskItemResponse)
async def get_risk_item(
    risk_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    item = (await db.execute(select(RiskItem).where(RiskItem.id == risk_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Risk item not found")
    return _risk_response(item)


@router.patch("/{risk_id}", response_model=RiskItemResponse)
async def update_risk_item(
    risk_id: int,
    data: RiskItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (await db.execute(select(RiskItem).where(RiskItem.id == risk_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Risk item not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    await log_artefact_activity(
        db,
        "risk",
        item.id,
        "updated",
        f"{current_user.full_name} updated risk {item.risk_id}",
    )
    return _risk_response(item)


@router.delete("/{risk_id}", status_code=204)
async def delete_risk_item(
    risk_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (await db.execute(select(RiskItem).where(RiskItem.id == risk_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Risk item not found")
    await log_artefact_activity(
        db,
        "risk",
        item.id,
        "deleted",
        f"{current_user.full_name} deleted risk {item.risk_id}",
    )
    await db.delete(item)
