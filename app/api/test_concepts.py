"""Test concepts API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    log_artefact_activity,
    log_document_workflow_activity_from_patch,
    should_log_generic_document_update,
    updated_summary,
)
from app.api.link_read_utils import merged_linked_requirement_ids_for_test_concept
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_role
from app.models import Project, TestConcept
from app.models.user import User, UserRole
from app.schemas import (
    PaginatedResponse,
    TestConceptCreate,
    TestConceptResponse,
    TestConceptUpdate,
)

router = APIRouter()


async def _response(db: AsyncSession, item: TestConcept) -> TestConceptResponse:
    merged = await merged_linked_requirement_ids_for_test_concept(
        db, item.id, item.linked_requirement_ids
    )
    return TestConceptResponse(
        id=item.id,
        project_id=item.project_id,
        concept_id=item.concept_id,
        name=item.name,
        description=item.description,
        status=item.status,
        linked_requirement_ids=merged,
        coverage=item.coverage,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("", response_model=PaginatedResponse[TestConceptResponse])
async def list_test_concepts(
    project_id: int = Query(..., description="Filter by project ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    base = select(TestConcept).where(TestConcept.project_id == project_id)
    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = base.order_by(TestConcept.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = [await _response(db, item) for item in result.scalars().all()]
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


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
        db, TestConcept, TestConcept.concept_id, data.project_id, project.prefix, "CPT"
    )

    existing = await db.execute(
        select(TestConcept).where(
            TestConcept.project_id == data.project_id,
            TestConcept.concept_id == concept_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Test concept with this ID already exists")

    item = TestConcept(
        project_id=data.project_id,
        concept_id=concept_id,
        name=data.name,
        description=data.description,
        status=data.status,
        linked_requirement_ids=None,
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
    return await _response(db, item)


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
    return await _response(db, item)


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

    fields_set = data.model_fields_set
    previous_status = item.status if "status" in fields_set else None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)
    await log_document_workflow_activity_from_patch(
        db,
        artefact_type="test-concept",
        artefact_id=item.id,
        public_id=item.concept_id,
        actor=current_user,
        fields_set=fields_set,
        previous_status=previous_status,
        next_status=item.status,
    )
    if should_log_generic_document_update(fields_set):
        await log_artefact_activity(
            db,
            "test-concept",
            item.id,
            "updated",
            updated_summary(current_user.full_name, "test concept", item.concept_id, fields_set),
        )
    return await _response(db, item)


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
