"""Design items API endpoints."""

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
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import DesignItem
from app.models.user import User
from app.schemas import (
    DesignItemCreate,
    DesignItemResponse,
    DesignItemUpdate,
    PaginatedResponse,
)

router = APIRouter()

KIND = ArtefactKind(
    model=DesignItem,
    type_code="DES",
    id_attr="design_id",
    activity_type="design",
    created_label="design item",
    updated_label="design item",
    not_found="Design item not found",
    exists="Design item with this ID already exists",
)


def _design_response(item: DesignItem) -> DesignItemResponse:
    return DesignItemResponse.model_validate(item)


@router.get("", response_model=PaginatedResponse[DesignItemResponse])
async def list_design_items(
    project_id: int = Query(..., description="Filter by project ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    return await list_items(db, KIND, project_id, skip, limit, current_user, _design_response)


@router.post("", response_model=DesignItemResponse, status_code=201)
async def create_design_item(
    data: DesignItemCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    item = await create_item(
        db,
        KIND,
        data.project_id,
        {
            "title": data.title,
            "description": data.description,
            "status": data.status,
            "priority": data.priority,
            "design_type": data.design_type,
            "visibility": data.visibility,
            "linked_requirement_id": None,
            "content_json": data.content_json,
            "content_html": data.content_html,
        },
        current_user,
    )
    return _design_response(item)


@router.get("/{design_id}", response_model=DesignItemResponse)
async def get_design_item(
    design_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    return _design_response(await get_item(db, KIND, design_id, current_user))


@router.patch("/{design_id}", response_model=DesignItemResponse)
async def update_design_item(
    design_id: int,
    data: DesignItemUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    item = await update_item(db, KIND, design_id, data, current_user)
    return _design_response(item)


@router.delete("/{design_id}", status_code=204)
async def delete_design_item(
    design_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    await delete_project_row(
        db,
        current_user,
        DesignItem,
        design_id,
        "Design item not found",
        resource="DES",
        audit_type="design",
        activity=("design item", "design_id"),
    )
