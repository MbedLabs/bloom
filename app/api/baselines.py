"""Baselines API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    apply_update,
    delete_project_row,
    fully_visible_types,
    get_row_or_404,
    get_visible_row,
    type_visible,
)
from app.core.database import get_db
from app.core.document_kinds import CANONICAL_DOCUMENT_KINDS
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_project_access
from app.models import (
    Baseline,
    ChangeRequest,
    DesignItem,
    Document,
    Project,
    Requirement,
    RiskItem,
    TestCase,
)
from app.models.user import User, UserRole
from app.schemas import BaselineCreate, BaselineResponse, BaselineUpdate
from app.services.audit import record_audit_event

BASELINE_NOT_FOUND = "Baseline not found"

router = APIRouter()

SNAPSHOT_SECTION_TYPES = {
    "requirements": ("REQ",),
    "test_cases": ("TC",),
    "documents": CANONICAL_DOCUMENT_KINDS,
    "designs": ("DES",),
    "risks": ("RSK",),
    "changes": ("CHG",),
}


def _baseline_response(
    item: Baseline, current_user: User, types: frozenset[str] | None
) -> BaselineResponse:
    """The baseline as the user sees it: no snapshot for an external user, else the
    snapshot sections whose document types are all in ``types``, the types of which the
    user sees every row."""
    response = BaselineResponse.model_validate(item)
    if current_user.role == UserRole.external:
        response.snapshot = None
    elif types is not None and response.snapshot is not None:
        response.snapshot = {
            section: value
            for section, value in response.snapshot.items()
            if all(type_visible(types, code) for code in SNAPSHOT_SECTION_TYPES.get(section, ()))
        }
    return response


async def _build_snapshot(db: AsyncSession, project_id: int) -> dict:
    requirements = (
        (await db.execute(select(Requirement).where(Requirement.project_id == project_id)))
        .scalars()
        .all()
    )
    test_cases = (
        (await db.execute(select(TestCase).where(TestCase.project_id == project_id)))
        .scalars()
        .all()
    )
    documents = (
        (await db.execute(select(Document).where(Document.project_id == project_id)))
        .scalars()
        .all()
    )
    designs = (
        (await db.execute(select(DesignItem).where(DesignItem.project_id == project_id)))
        .scalars()
        .all()
    )
    risks = (
        (await db.execute(select(RiskItem).where(RiskItem.project_id == project_id)))
        .scalars()
        .all()
    )
    changes = (
        (await db.execute(select(ChangeRequest).where(ChangeRequest.project_id == project_id)))
        .scalars()
        .all()
    )

    return {
        "requirements": {
            "count": len(requirements),
            "ids": [item.req_id for item in requirements],
        },
        "test_cases": {
            "count": len(test_cases),
            "ids": [item.tc_id for item in test_cases],
        },
        "documents": {
            "count": len(documents),
            "titles": [item.title for item in documents],
        },
        "designs": {"count": len(designs), "ids": [item.design_id for item in designs]},
        "risks": {"count": len(risks), "ids": [item.risk_id for item in risks]},
        "changes": {"count": len(changes), "ids": [item.change_id for item in changes]},
    }


@router.get(
    "", response_model=list[BaselineResponse], responses={400: {"description": "Bad Request"}}
)
async def list_baselines(
    project_id: int | None = Query(None, description="Optional project filter"),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    if project_id is not None:
        await require_project_access(db, current_user, project_id, permission=("view", "baseline"))
    query = select(Baseline).order_by(Baseline.created_at.desc())
    if project_id:
        query = query.where(Baseline.project_id == project_id)
    elif current_user.role != UserRole.admin:
        raise HTTPException(status_code=400, detail="project_id is required for non-admin users")
    result = await db.execute(query)
    types = await fully_visible_types(db, current_user, project_id) if project_id else None
    return [_baseline_response(item, current_user, types) for item in result.scalars().all()]


@router.post("", response_model=BaselineResponse, status_code=201)
async def create_baseline(
    data: BaselineCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    project = await get_row_or_404(db, Project, data.project_id, "Project not found")

    await require_project_access(
        db,
        current_user,
        data.project_id,
        permission=("create", "baseline"),
    )

    baseline_id = await next_doc_id(
        db, Baseline, Baseline.baseline_id, data.project_id, project.prefix, "BL"
    )
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
    await record_audit_event(
        db,
        "baseline.created",
        target_type="baseline",
        target_id=item.baseline_id,
        project_id=item.project_id,
    )
    await db.refresh(item)
    return _baseline_response(
        item, current_user, await fully_visible_types(db, current_user, item.project_id)
    )


@router.get(
    "/{baseline_id}", response_model=BaselineResponse, responses={404: {"description": "Not Found"}}
)
async def get_baseline(
    baseline_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    item = (
        await db.execute(select(Baseline).where(Baseline.id == baseline_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=BASELINE_NOT_FOUND)
    await require_project_access(db, current_user, item.project_id, permission=("view", "baseline"))
    return _baseline_response(
        item, current_user, await fully_visible_types(db, current_user, item.project_id)
    )


@router.patch("/{baseline_id}", response_model=BaselineResponse)
async def update_baseline(
    baseline_id: int,
    data: BaselineUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    item = await get_visible_row(
        db,
        Baseline,
        baseline_id,
        BASELINE_NOT_FOUND,
        current_user,
        permission=("edit", "baseline"),
    )
    await apply_update(db, item, data, "baseline")
    return _baseline_response(
        item, current_user, await fully_visible_types(db, current_user, item.project_id)
    )


@router.delete("/{baseline_id}", status_code=204)
async def delete_baseline(
    baseline_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    await delete_project_row(
        db,
        current_user,
        Baseline,
        baseline_id,
        BASELINE_NOT_FOUND,
        resource="baseline",
        audit_type="baseline",
    )
