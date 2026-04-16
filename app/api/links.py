"""Generic typed artefact link endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models import ArtefactLink, Project
from app.models.user import User, UserRole
from app.schemas import ArtefactLinkCreate, ArtefactLinkResponse

router = APIRouter()


@router.get("", response_model=list[ArtefactLinkResponse])
async def list_links(
    project_id: int = Query(...),
    source_type: str | None = Query(None),
    source_id: int | None = Query(None),
    target_type: str | None = Query(None),
    target_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    query = select(ArtefactLink).where(ArtefactLink.project_id == project_id)
    if source_type:
        query = query.where(ArtefactLink.source_type == source_type)
    if source_id is not None:
        query = query.where(ArtefactLink.source_id == source_id)
    if target_type:
        query = query.where(ArtefactLink.target_type == target_type)
    if target_id is not None:
        query = query.where(ArtefactLink.target_id == target_id)
    rows = (await db.execute(query.order_by(ArtefactLink.created_at.desc()))).scalars().all()
    return [ArtefactLinkResponse.model_validate(row) for row in rows]


@router.post("", response_model=ArtefactLinkResponse, status_code=201)
async def create_link(
    data: ArtefactLinkCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    project = (
        await db.execute(select(Project).where(Project.id == data.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = (
        await db.execute(
            select(ArtefactLink).where(
                ArtefactLink.source_type == data.source_type,
                ArtefactLink.source_id == data.source_id,
                ArtefactLink.target_type == data.target_type,
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
    return ArtefactLinkResponse.model_validate(link)


@router.delete("/{link_id}", status_code=204)
async def delete_link(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    link = (
        await db.execute(select(ArtefactLink).where(ArtefactLink.id == link_id))
    ).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await db.delete(link)
