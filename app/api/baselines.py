"""Baselines API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_role
from app.models import Baseline, ChangeRequest, DesignItem, Document, Project, Requirement, RiskItem, TestCase
from app.models.user import User, UserRole
from app.schemas import BaselineCreate, BaselineResponse, BaselineUpdate

router = APIRouter()


def _baseline_response(item: Baseline) -> BaselineResponse:
    return BaselineResponse.model_validate(item)


async def _build_snapshot(db: AsyncSession, project_id: int) -> dict:
    requirements = (await db.execute(select(Requirement).where(Requirement.project_id == project_id))).scalars().all()
    test_cases = (await db.execute(select(TestCase).where(TestCase.project_id == project_id))).scalars().all()
    documents = (await db.execute(select(Document).where(Document.project_id == project_id))).scalars().all()
    designs = (await db.execute(select(DesignItem).where(DesignItem.project_id == project_id))).scalars().all()
    risks = (await db.execute(select(RiskItem).where(RiskItem.project_id == project_id))).scalars().all()
    changes = (await db.execute(select(ChangeRequest).where(ChangeRequest.project_id == project_id))).scalars().all()

    return {
        "requirements": {"count": len(requirements), "ids": [item.req_id for item in requirements]},
        "test_cases": {"count": len(test_cases), "ids": [item.tc_id for item in test_cases]},
        "documents": {"count": len(documents), "titles": [item.title for item in documents]},
        "designs": {"count": len(designs), "ids": [item.design_id for item in designs]},
        "risks": {"count": len(risks), "ids": [item.risk_id for item in risks]},
        "changes": {"count": len(changes), "ids": [item.change_id for item in changes]},
    }


@router.get("", response_model=list[BaselineResponse])
async def list_baselines(
    project_id: int | None = Query(None, description="Optional project filter"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    query = select(Baseline).order_by(Baseline.created_at.desc())
    if project_id:
        query = query.where(Baseline.project_id == project_id)
    result = await db.execute(query)
    return [_baseline_response(item) for item in result.scalars().all()]


@router.post("", response_model=BaselineResponse, status_code=201)
async def create_baseline(
    data: BaselineCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    project = (await db.execute(select(Project).where(Project.id == data.project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    baseline_id = await next_doc_id(db, Baseline, Baseline.baseline_id, data.project_id, project.prefix, "BL")
    item = Baseline(
        project_id=data.project_id,
        baseline_id=baseline_id,
        name=data.name,
        description=data.description,
        baseline_type=data.baseline_type,
        snapshot=await _build_snapshot(db, data.project_id),
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return _baseline_response(item)


@router.get("/{baseline_id}", response_model=BaselineResponse)
async def get_baseline(
    baseline_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    item = (await db.execute(select(Baseline).where(Baseline.id == baseline_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return _baseline_response(item)


@router.patch("/{baseline_id}", response_model=BaselineResponse)
async def update_baseline(
    baseline_id: int,
    data: BaselineUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (await db.execute(select(Baseline).where(Baseline.id == baseline_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Baseline not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    return _baseline_response(item)


@router.delete("/{baseline_id}", status_code=204)
async def delete_baseline(
    baseline_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (await db.execute(select(Baseline).where(Baseline.id == baseline_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Baseline not found")
    await db.delete(item)
