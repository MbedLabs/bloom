"""Test concepts API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import log_artefact_activity
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_role
from app.models import Project, TestConcept
from app.models.user import User, UserRole
from app.schemas import TestConceptCreate, TestConceptResponse, TestConceptUpdate

router = APIRouter()


def _response(item: TestConcept) -> TestConceptResponse:
    return TestConceptResponse(
        id=item.id,
        project_id=item.project_id,
        concept_id=item.concept_id,
        name=item.name,
        description=item.description,
        status=item.status,
        linked_requirement_ids=item.linked_requirement_ids or [],
        coverage=item.coverage,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("", response_model=list[TestConceptResponse])
async def list_test_concepts(
    project_id: int = Query(..., description="Filter by project ID"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TestConcept)
        .where(TestConcept.project_id == project_id)
        .order_by(TestConcept.created_at.desc())
    )
    return [_response(item) for item in result.scalars().all()]


@router.post("", response_model=TestConceptResponse, status_code=201)
async def create_test_concept(
    data: TestConceptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    project = (
        await db.execute(select(Project).where(Project.id == data.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    concept_id = await next_doc_id(
        db, TestConcept, TestConcept.concept_id, data.project_id, project.prefix, "TCO"
    )
    item = TestConcept(
        project_id=data.project_id,
        concept_id=concept_id,
        name=data.name,
        description=data.description,
        status=data.status,
        linked_requirement_ids=data.linked_requirement_ids,
        coverage=data.coverage,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await log_artefact_activity(
        db,
        "test-concept",
        item.id,
        "created",
        f"{current_user.full_name} created test concept {item.concept_id}",
    )
    return _response(item)


@router.get("/{concept_id}", response_model=TestConceptResponse)
async def get_test_concept(
    concept_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    item = (
        await db.execute(select(TestConcept).where(TestConcept.id == concept_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Test concept not found")
    return _response(item)


@router.patch("/{concept_id}", response_model=TestConceptResponse)
async def update_test_concept(
    concept_id: int,
    data: TestConceptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (
        await db.execute(select(TestConcept).where(TestConcept.id == concept_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Test concept not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    await log_artefact_activity(
        db,
        "test-concept",
        item.id,
        "updated",
        f"{current_user.full_name} updated test concept {item.concept_id}",
    )
    return _response(item)


@router.delete("/{concept_id}", status_code=204)
async def delete_test_concept(
    concept_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (
        await db.execute(select(TestConcept).where(TestConcept.id == concept_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Test concept not found")
    await log_artefact_activity(
        db,
        "test-concept",
        item.id,
        "deleted",
        f"{current_user.full_name} deleted test concept {item.concept_id}",
    )
    await db.delete(item)
