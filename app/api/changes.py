"""Change requests API endpoints."""

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
from app.models import ChangeRequest
from app.models.user import User
from app.schemas import (
    ChangeRequestCreate,
    ChangeRequestResponse,
    ChangeRequestUpdate,
    PaginatedResponse,
)

router = APIRouter()

KIND = ArtefactKind(
    model=ChangeRequest,
    type_code="CHG",
    id_attr="change_id",
    activity_type="change",
    created_label="change request",
    updated_label="change request",
    not_found="Change request not found",
    exists="Change request with this ID already exists",
)


def _change_response(item: ChangeRequest) -> ChangeRequestResponse:
    return ChangeRequestResponse.model_validate(item)


@router.get("", response_model=PaginatedResponse[ChangeRequestResponse])
async def list_change_requests(
    project_id: int = Query(..., description="Filter by project ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    return await list_items(db, KIND, project_id, skip, limit, current_user, _change_response)


@router.post("", response_model=ChangeRequestResponse, status_code=201)
async def create_change_request(
    data: ChangeRequestCreate,
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
            "change_type": data.change_type,
            "impact_assessment": data.impact_assessment,
            "justification": data.justification,
            "visibility": data.visibility,
            "content_json": data.content_json,
            "content_html": data.content_html,
        },
        current_user,
        named=data.model_dump(exclude_unset=True),
        tag_ids=data.tag_ids,
    )
    return _change_response(item)


@router.get("/{change_id}", response_model=ChangeRequestResponse)
async def get_change_request(
    change_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    return _change_response(await get_item(db, KIND, change_id, current_user))


@router.patch("/{change_id}", response_model=ChangeRequestResponse)
async def update_change_request(
    change_id: int,
    data: ChangeRequestUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    item = await update_item(db, KIND, change_id, data, current_user)

    syncable_fields = {"title", "status", "description"}
    updates = data.model_dump(exclude_unset=True)
    changed_sync_fields = {k: v for k, v in updates.items() if k in syncable_fields}
    if changed_sync_fields and item.external_tracker:
        from app.api.integrations import sync_change_request_to_tracker

        await sync_change_request_to_tracker(db, item, changed_sync_fields)
    return _change_response(item)


@router.delete("/{change_id}", status_code=204)
async def delete_change_request(
    change_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    await delete_project_row(
        db,
        current_user,
        ChangeRequest,
        change_id,
        "Change request not found",
        resource="CHG",
        audit_type="change",
        activity=("change request", "change_id"),
    )
