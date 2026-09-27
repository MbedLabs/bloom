"""Test concepts API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_crud import (
    ArtefactKind,
    create_item,
    get_item,
    list_items,
    update_item,
)
from app.api.artefact_utils import delete_project_row
from app.api.link_read_utils import merged_linked_requirement_ids_for_test_concept
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import TestConcept
from app.models.user import User
from app.schemas import (
    PaginatedResponse,
    TestConceptCreate,
    TestConceptResponse,
    TestConceptUpdate,
)

router = APIRouter()

KIND = ArtefactKind(
    model=TestConcept,
    type_code="CPT",
    id_attr="concept_id",
    activity_type="test-concept",
    created_label="test concept",
    updated_label="test concept",
    not_found="Test concept not found",
    exists="Test concept with this ID already exists",
)


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
        visibility=item.visibility,
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
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    return await list_items(
        db, KIND, project_id, skip, limit, current_user, lambda item: _response(db, item)
    )


@router.post("", response_model=TestConceptResponse, status_code=201)
async def create_test_concept(
    data: TestConceptCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    item = await create_item(
        db,
        KIND,
        data.project_id,
        {
            "name": data.name,
            "description": data.description,
            "status": data.status,
            "visibility": data.visibility,
            "linked_requirement_ids": None,
            "coverage": data.coverage,
            "content_json": data.content_json,
            "content_html": data.content_html,
        },
        current_user,
    )
    return await _response(db, item)


@router.get("/{concept_id}", response_model=TestConceptResponse)
async def get_test_concept(
    concept_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    return await _response(db, await get_item(db, KIND, concept_id, current_user))


@router.patch("/{concept_id}", response_model=TestConceptResponse)
async def update_test_concept(
    concept_id: int,
    data: TestConceptUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    item = await update_item(db, KIND, concept_id, data, current_user)
    return await _response(db, item)


@router.delete("/{concept_id}", status_code=204)
async def delete_test_concept(
    concept_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    await delete_project_row(
        db,
        current_user,
        TestConcept,
        concept_id,
        "Test concept not found",
        resource="CPT",
        audit_type="test-concept",
        activity=("test concept", "concept_id"),
    )
