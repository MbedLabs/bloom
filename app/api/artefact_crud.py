"""List, read, create and update for the controlled artefact types."""

import inspect
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    audit_visibility_change,
    get_row_or_404,
    get_visible_row,
    log_artefact_activity,
    log_document_workflow_activity_from_patch,
    page_of,
    should_log_generic_document_update,
    updated_summary,
)
from app.core.id_generator import next_doc_id
from app.core.security import apply_external_visibility_filter, require_project_access
from app.models import Project
from app.models.user import User
from app.schemas import PaginatedResponse
from app.services.tag_links import sync_tag_links


@dataclass(frozen=True)
class ArtefactKind:
    """How one controlled artefact type is stored, checked and described."""

    model: Any
    type_code: str
    id_attr: str
    activity_type: str
    created_label: str
    updated_label: str
    not_found: str
    exists: str


async def _respond(respond: Callable, item):
    response = respond(item)
    return await response if inspect.isawaitable(response) else response


async def list_items(
    db: AsyncSession,
    kind: ArtefactKind,
    project_id: int,
    skip: int,
    limit: int,
    current_user: User,
    respond: Callable,
) -> PaginatedResponse:
    """One page of the project's artefacts of the kind, newest first."""
    model = kind.model
    await require_project_access(db, current_user, project_id)

    base = select(model).where(model.project_id == project_id)
    base = apply_external_visibility_filter(base, model, current_user)
    rows, total = await page_of(db, base, model, skip, limit)
    items = [await _respond(respond, item) for item in rows]
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


async def get_item(db: AsyncSession, kind: ArtefactKind, item_id: int, current_user: User):
    """The artefact of the kind with the id, when the user may see it."""
    return await get_visible_row(db, kind.model, item_id, kind.not_found, current_user)


async def create_item(
    db: AsyncSession, kind: ArtefactKind, project_id: int, fields: dict, current_user: User
):
    """Create an artefact of the kind with the next id of the project and the fields."""
    model = kind.model
    id_column = getattr(model, kind.id_attr)
    project = await get_row_or_404(db, Project, project_id, "Project not found")

    await require_project_access(
        db,
        current_user,
        project_id,
        permission=("create", kind.type_code),
    )

    public_id = await next_doc_id(db, model, id_column, project_id, project.prefix, kind.type_code)

    existing = await db.execute(
        select(model).where(
            model.project_id == project_id,
            id_column == public_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=kind.exists)

    item = model(project_id=project_id, **{kind.id_attr: public_id}, **fields)
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await sync_tag_links(
        db,
        project_id=item.project_id,
        source_type=kind.type_code,
        source_id=item.id,
        content_json=item.content_json,
    )
    await log_artefact_activity(
        db,
        kind.activity_type,
        item.id,
        "created",
        f"{current_user.full_name} created {kind.created_label} {public_id}",
    )
    return item


async def update_item(db: AsyncSession, kind: ArtefactKind, item_id: int, data, current_user: User):
    """Apply the set fields of the update to the artefact and log what changed."""
    model = kind.model
    item = (await db.execute(select(model).where(model.id == item_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=kind.not_found)

    await require_project_access(
        db,
        current_user,
        item.project_id,
        permission=("edit", kind.type_code),
    )

    fields_set = data.model_fields_set
    previous_status = item.status if "status" in fields_set else None

    previous_visibility = getattr(item, "visibility", None)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await audit_visibility_change(db, kind.activity_type, item, previous_visibility)
    if item.content_json is not None and "content_json" in fields_set:
        await sync_tag_links(
            db,
            project_id=item.project_id,
            source_type=kind.type_code,
            source_id=item.id,
            content_json=item.content_json,
        )

    await db.flush()
    await db.refresh(item)
    public_id = getattr(item, kind.id_attr)
    await log_document_workflow_activity_from_patch(
        db,
        artefact_type=kind.activity_type,
        artefact_id=item.id,
        public_id=public_id,
        actor=current_user,
        fields_set=fields_set,
        previous_status=previous_status,
        next_status=item.status,
    )
    if should_log_generic_document_update(fields_set):
        await log_artefact_activity(
            db,
            kind.activity_type,
            item.id,
            "updated",
            updated_summary(current_user.full_name, kind.updated_label, public_id, fields_set),
        )
    return item
