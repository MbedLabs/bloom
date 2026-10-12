"""The tag base, managed by administrators, and the tags each artefact carries (R-t)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import get_visible_row
from app.core.database import get_db
from app.core.security import (
    covers_with_tags,
    effective_permissions,
    get_current_user,
    has_permission,
    require_app_permission,
    require_project_access,
    tag_scope,
)
from app.models.tags import TAGGED_MODELS, TYPE_CODES, ArtefactTag, Tag
from app.models.user import User, UserRole
from app.schemas.tags import (
    ArtefactTagsUpdate,
    TagCreate,
    TagResponse,
    TagScopeResponse,
    TagUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter()

require_admin = require_app_permission("view")


def _model(artefact_type: str):
    model = TAGGED_MODELS.get(artefact_type)
    if model is None:
        raise HTTPException(status_code=404, detail="Unknown artefact type")
    return model


async def _carried(db: AsyncSession, artefact_type: str, artefact_id: int) -> set[int]:
    return set(
        (
            await db.execute(
                select(ArtefactTag.tag_id).where(
                    ArtefactTag.artefact_type == artefact_type,
                    ArtefactTag.artefact_id == artefact_id,
                )
            )
        )
        .scalars()
        .all()
    )


async def _tags(db: AsyncSession, ids) -> list[Tag]:
    if not ids:
        return []
    return list(
        (await db.execute(select(Tag).where(Tag.id.in_(ids)).order_by(Tag.name))).scalars().all()
    )


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(
    project_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """List the origin catalogue for Access Management or the user's project tag scope."""
    if project_id is None or current_user.role == UserRole.admin:
        if project_id is None and not has_permission(
            await effective_permissions(db, current_user, None), "view", "access"
        ):
            raise HTTPException(status_code=403, detail="A project is required.")
        return list((await db.execute(select(Tag).order_by(Tag.name))).scalars().all())
    await require_project_access(db, current_user, project_id)
    scope = await tag_scope(db, current_user, project_id)
    if scope is None:
        return list((await db.execute(select(Tag).order_by(Tag.name))).scalars().all())
    return await _tags(db, scope)


@router.get("/tags/scope", response_model=TagScopeResponse)
async def my_tag_scope(
    project_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Whether the user's policies choose tags on the project, and the tags they may give
    a new artefact there."""
    await require_project_access(db, current_user, project_id)
    scope = await tag_scope(db, current_user, project_id)
    if scope is None:
        every = (await db.execute(select(Tag).order_by(Tag.name))).scalars().all()
        return TagScopeResponse(limited=False, tags=list(every))
    return TagScopeResponse(limited=True, tags=await _tags(db, scope))


@router.post("/tags", response_model=TagResponse, status_code=201)
async def create_tag(
    data: TagCreate,
    _admin: User = Depends(require_app_permission("create")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Add a tag to the base."""
    name = data.name.strip()
    if (await db.execute(select(Tag.id).where(Tag.name == name))).first():
        raise HTTPException(status_code=409, detail="A tag with this name already exists")
    tag = Tag(name=name)
    db.add(tag)
    await db.flush()
    await record_audit_event(
        db, "tag.created", target_type="tag", target_id=tag.id, details={"name": name}
    )
    await db.refresh(tag)
    return tag


@router.patch("/tags/{tag_id}", response_model=TagResponse)
async def rename_tag(
    tag_id: int,
    data: TagUpdate,
    _admin: User = Depends(require_app_permission("edit")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Rename a tag; artefacts and policies keep it."""
    tag = await db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    name = data.name.strip()
    clash = (await db.execute(select(Tag.id).where(Tag.name == name, Tag.id != tag_id))).first()
    if clash:
        raise HTTPException(status_code=409, detail="A tag with this name already exists")
    previous = tag.name
    tag.name = name
    await db.flush()
    await record_audit_event(
        db,
        "tag.renamed",
        target_type="tag",
        target_id=tag.id,
        details={"from": previous, "to": name},
    )
    await db.refresh(tag)
    return tag


@router.get("/artefacts/{artefact_type}/{artefact_id}/tags", response_model=list[TagResponse])
async def artefact_tags(
    artefact_type: str,
    artefact_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """The tags the artefact carries, those inside the user's scope."""
    row = await get_visible_row(
        db,
        _model(artefact_type),
        artefact_id,
        "Artefact not found",
        current_user,
        permission=("view", TYPE_CODES[artefact_type]),
    )
    carried = await _carried(db, artefact_type, row.id)
    scope = await tag_scope(
        db, current_user, row.project_id, TYPE_CODES[artefact_type] or row.doc_type
    )
    return await _tags(db, carried if scope is None else carried & scope)


@router.put("/artefacts/{artefact_type}/{artefact_id}/tags", response_model=list[TagResponse])
async def set_artefact_tags(
    artefact_type: str,
    artefact_id: int,
    data: ArtefactTagsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Set the tags the artefact carries. It needs edit on the artefact; external users set
    tags only when creating; a user adds and removes only the tags their policies tick for
    the artefact's type, keeps the others, and the artefact stays covered by their edit."""
    row = await get_visible_row(
        db,
        _model(artefact_type),
        artefact_id,
        "Artefact not found",
        current_user,
        permission=("edit", TYPE_CODES[artefact_type]),
    )
    if current_user.role == UserRole.external:
        raise HTTPException(status_code=403, detail="External users set tags only when creating.")
    wanted = set(data.tag_ids)
    known = {t.id for t in await _tags(db, wanted)}
    if wanted - known:
        raise HTTPException(status_code=400, detail=f"Unknown tags: {sorted(wanted - known)}")
    carried = await _carried(db, artefact_type, row.id)
    type_code = TYPE_CODES[artefact_type] or row.doc_type
    scope = await tag_scope(db, current_user, row.project_id, type_code, "edit")
    if scope is not None:
        if wanted - scope - carried:
            raise HTTPException(
                status_code=403, detail="Only tags your policies tick can be added or removed."
            )
        wanted = (wanted & scope) | (carried - scope)
    if not await covers_with_tags(db, current_user, row, "edit", wanted):
        raise HTTPException(status_code=403, detail="The artefact must stay inside your policies.")
    removed, added = carried - wanted, wanted - carried
    if removed:
        await db.execute(
            delete(ArtefactTag).where(
                ArtefactTag.artefact_type == artefact_type,
                ArtefactTag.artefact_id == row.id,
                ArtefactTag.tag_id.in_(removed),
            )
        )
    for tag_id in sorted(added):
        db.add(
            ArtefactTag(
                tag_id=tag_id,
                artefact_type=artefact_type,
                artefact_id=row.id,
                project_id=row.project_id,
            )
        )
    await db.flush()
    if removed or added:
        await record_audit_event(
            db,
            "artefact.tags_changed",
            target_type=artefact_type,
            target_id=row.id,
            project_id=row.project_id,
            details={"added": sorted(added), "removed": sorted(removed)},
        )
    seen = await tag_scope(db, current_user, row.project_id, type_code)
    return await _tags(db, wanted if seen is None else wanted & seen)
