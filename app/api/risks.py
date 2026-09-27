"""Risk items API endpoints."""

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
from app.models import RiskItem
from app.models.user import User
from app.schemas import (
    PaginatedResponse,
    RiskItemCreate,
    RiskItemResponse,
    RiskItemUpdate,
)

router = APIRouter()

KIND = ArtefactKind(
    model=RiskItem,
    type_code="RSK",
    id_attr="risk_id",
    activity_type="risk",
    created_label="risk",
    updated_label="risk item",
    not_found="Risk item not found",
    exists="Risk item with this ID already exists",
)


def _risk_response(item: RiskItem) -> RiskItemResponse:
    return RiskItemResponse.model_validate(item)


@router.get("", response_model=PaginatedResponse[RiskItemResponse])
async def list_risk_items(
    project_id: int = Query(..., description="Filter by project ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    return await list_items(db, KIND, project_id, skip, limit, current_user, _risk_response)


@router.post("", response_model=RiskItemResponse, status_code=201)
async def create_risk_item(
    data: RiskItemCreate,
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
            "severity": data.severity,
            "probability": data.probability,
            "mitigation": data.mitigation,
            "risk_category": data.risk_category,
            "visibility": data.visibility,
            "linked_requirement_id": None,
            "content_json": data.content_json,
            "content_html": data.content_html,
        },
        current_user,
    )
    return _risk_response(item)


@router.get("/{risk_id}", response_model=RiskItemResponse)
async def get_risk_item(
    risk_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    return _risk_response(await get_item(db, KIND, risk_id, current_user))


@router.patch("/{risk_id}", response_model=RiskItemResponse)
async def update_risk_item(
    risk_id: int,
    data: RiskItemUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    item = await update_item(db, KIND, risk_id, data, current_user)
    return _risk_response(item)


@router.delete("/{risk_id}", status_code=204)
async def delete_risk_item(
    risk_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    await delete_project_row(
        db,
        current_user,
        RiskItem,
        risk_id,
        "Risk item not found",
        resource="RSK",
        audit_type="risk",
        activity=("risk", "risk_id"),
    )
