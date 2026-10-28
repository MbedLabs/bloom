"""Generic typed artefact link endpoints."""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    changes_allowed,
    get_row_or_404,
    get_visible_row,
    type_visible,
    visible_types,
)
from app.core.database import get_db
from app.core.link_rules import (
    get_allowed_link_roles,
    get_linkable_type_storage_values,
    is_allowed_link_role,
    is_known_linkable_type,
    normalize_linkable_type,
)
from app.core.security import (
    get_current_user,
    get_external_doc_types,
    require_project_access,
)
from app.models import ArtefactLink, Project
from app.models.user import User, UserRole
from app.schemas import ArtefactLinkCreate, ArtefactLinkResponse
from app.services.audit import mark_refused
from app.services.tag_links import link_end

router = APIRouter()


def _link_response(row: ArtefactLink) -> ArtefactLinkResponse:
    response = ArtefactLinkResponse.model_validate(row)
    return response.model_copy(
        update={
            "source_type": normalize_linkable_type(response.source_type),
            "target_type": normalize_linkable_type(response.target_type),
        }
    )


@router.get("", response_model=list[ArtefactLinkResponse])
async def list_links(
    project_id: int = Query(...),
    source_type: str | None = Query(None),
    source_id: int | None = Query(None),
    target_type: str | None = Query(None),
    target_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    await require_project_access(db, current_user, project_id, permission=("view", "link"))
    await get_external_doc_types(db, current_user, project_id)

    query = select(ArtefactLink).where(ArtefactLink.project_id == project_id)
    if source_type:
        query = query.where(
            ArtefactLink.source_type.in_(get_linkable_type_storage_values(source_type))
        )
    if source_id is not None:
        query = query.where(ArtefactLink.source_id == source_id)
    if target_type:
        query = query.where(
            ArtefactLink.target_type.in_(get_linkable_type_storage_values(target_type))
        )
    if target_id is not None:
        query = query.where(ArtefactLink.target_id == target_id)
    rows = (await db.execute(query.order_by(ArtefactLink.created_at.desc()))).scalars().all()
    types = await visible_types(db, current_user, project_id)
    rows = [
        row
        for row in rows
        if type_visible(types, normalize_linkable_type(row.source_type))
        and type_visible(types, normalize_linkable_type(row.target_type))
    ]

    if current_user.role != UserRole.admin:
        visible_rows = []
        for row in rows:
            ends = (row.source_type, row.source_id), (row.target_type, row.target_id)
            if all(
                [
                    (await link_end(db, project_id, kind, item, current_user))[1]
                    for kind, item in ends
                ]
            ):
                visible_rows.append(row)
        rows = visible_rows

    return [_link_response(row) for row in rows]


@router.post(
    "",
    response_model=ArtefactLinkResponse,
    status_code=201,
    responses={
        403: {"description": HTTPStatus(403).phrase},
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        422: {"description": "Unprocessable Content"},
    },
)
async def create_link(
    data: ArtefactLinkCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    data.source_type = normalize_linkable_type(data.source_type)
    data.target_type = normalize_linkable_type(data.target_type)

    await get_row_or_404(db, Project, data.project_id, "Project not found")
    await require_project_access(
        db,
        current_user,
        data.project_id,
        permission=("create", "link"),
    )
    if not is_known_linkable_type(data.source_type) or not is_known_linkable_type(data.target_type):
        raise HTTPException(status_code=422, detail="Unsupported relationship document kind")
    if data.source_type == data.target_type and data.source_id == data.target_id:
        raise HTTPException(status_code=400, detail="A document cannot link to itself")
    if not is_allowed_link_role(data.source_type, data.target_type, data.role):
        allowed_roles = get_allowed_link_roles(data.source_type, data.target_type)
        if not allowed_roles:
            raise HTTPException(
                status_code=422,
                detail=f"Relationships from {data.source_type} to {data.target_type} are not allowed",
            )
        raise HTTPException(
            status_code=422,
            detail=(
                f"Role '{data.role}' is not allowed for "
                f"{data.source_type} -> {data.target_type}. Allowed roles: {', '.join(allowed_roles)}"
            ),
        )
    await get_external_doc_types(db, current_user, data.project_id)
    source, source_visible = await link_end(
        db,
        data.project_id,
        data.source_type,
        data.source_id,
        current_user,
    )
    if not source_visible:
        if source is not None:
            mark_refused()
        raise HTTPException(status_code=404, detail="Source document not found in project")
    target, target_visible = await link_end(
        db,
        data.project_id,
        data.target_type,
        data.target_id,
        current_user,
    )
    if not target_visible:
        if target is not None:
            mark_refused()
        raise HTTPException(status_code=404, detail="Target document not found in project")
    if not (changes_allowed(current_user, source) and changes_allowed(current_user, target)):
        raise HTTPException(status_code=403, detail="External users change only what they created.")
    existing = (
        await db.execute(
            select(ArtefactLink).where(
                ArtefactLink.project_id == data.project_id,
                ArtefactLink.source_type.in_(get_linkable_type_storage_values(data.source_type)),
                ArtefactLink.source_id == data.source_id,
                ArtefactLink.target_type.in_(get_linkable_type_storage_values(data.target_type)),
                ArtefactLink.target_id == data.target_id,
                ArtefactLink.role == data.role,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Link already exists")

    link = ArtefactLink(**data.model_dump())
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return _link_response(link)


@router.delete(
    "/{link_id}",
    status_code=204,
    responses={403: {"description": HTTPStatus(403).phrase}, 404: {"description": "Not Found"}},
)
async def delete_link(
    link_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    link = await get_visible_row(db, ArtefactLink, link_id, "Link not found", current_user)
    await get_external_doc_types(db, current_user, link.project_id)
    ends = [
        await link_end(db, link.project_id, kind, item, current_user)
        for kind, item in ((link.source_type, link.source_id), (link.target_type, link.target_id))
    ]
    if any(row is not None and not visible for row, visible in ends):
        mark_refused()
        raise HTTPException(status_code=404, detail="Link not found")
    await require_project_access(db, current_user, link.project_id, permission=("delete", "link"))
    if current_user.role == UserRole.external and not all(
        row is not None and changes_allowed(current_user, row) for row, _ in ends
    ):
        raise HTTPException(status_code=403, detail="External users change only what they created.")
    await db.delete(link)
