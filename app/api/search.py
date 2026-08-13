"""Global cross-artefact search."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.search_registry import SEARCH_TARGETS, rank_match
from app.core.security import get_current_user
from app.models import Project, ProjectExternalDocType, ProjectMembership
from app.models.models import ArtefactVisibility
from app.models.user import User, UserRole

router = APIRouter()

PER_TYPE_LIMIT = 8
MIN_QUERY_LENGTH = 2


class SearchResultItem(BaseModel):
    type: str  # canonical type code: REQ, TC, DES, ... or a Document's own doc_type
    id: int
    doc_id: Optional[str] = None
    title: str
    status: Optional[str] = None
    project_id: int
    project_prefix: str
    project_name: str


class SearchResponse(BaseModel):
    query: str
    total: int
    items: List[SearchResultItem]


async def _accessible_projects(db: AsyncSession, user: User) -> dict[int, Project]:
    if user.role == UserRole.admin:
        rows = (await db.execute(select(Project))).scalars().all()
    else:
        rows = (
            (
                await db.execute(
                    select(Project)
                    .join(ProjectMembership, ProjectMembership.project_id == Project.id)
                    .where(ProjectMembership.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
    return {p.id: p for p in rows}


async def _external_allowed_types(
    db: AsyncSession, user: User, project_ids: list[int]
) -> Optional[dict[int, set[str]]]:
    """For external users: project_id -> allowed doc-type codes. Others: None."""
    if user.role != UserRole.external or not project_ids:
        return None if user.role != UserRole.external else {}
    rows = (
        await db.execute(
            select(ProjectMembership.project_id, ProjectExternalDocType.doc_type)
            .join(
                ProjectExternalDocType,
                ProjectExternalDocType.membership_id == ProjectMembership.id,
            )
            .where(
                ProjectMembership.user_id == user.id,
                ProjectMembership.project_id.in_(project_ids),
            )
        )
    ).all()
    allowed: dict[int, set[str]] = {}
    for project_id, doc_type in rows:
        allowed.setdefault(project_id, set()).add(doc_type)
    return allowed


async def run_global_search(
    db: AsyncSession,
    current_user: User,
    q: str,
    project_id: Optional[int] = None,
    limit: int = 25,
) -> SearchResponse:
    """Search artefacts by human ID and title across accessible projects.

    Results are ranked (exact ID, ID prefix, title prefix, substrings) and
    capped per type before the global limit. External users only see artefact
    types allowed by their membership and customer-visible artefacts.
    """
    projects = await _accessible_projects(db, current_user)
    if project_id is not None:
        projects = {pid: p for pid, p in projects.items() if pid == project_id}
    if not projects:
        return SearchResponse(query=q, total=0, items=[])

    project_ids = list(projects)
    external_allowed = await _external_allowed_types(db, current_user, project_ids)

    pattern = f"%{q}%"
    query_lower = q.lower()
    candidates: list[tuple[int, SearchResultItem]] = []

    for target in SEARCH_TARGETS:
        model = target.model
        id_col = getattr(model, target.id_attr)
        title_col = getattr(model, target.title_attr)

        stmt = select(model).where(
            model.project_id.in_(project_ids),
            or_(id_col.ilike(pattern), title_col.ilike(pattern)),
        )
        if current_user.role == UserRole.external:
            stmt = stmt.where(model.visibility == ArtefactVisibility.customer.value)
        stmt = stmt.limit(PER_TYPE_LIMIT * 3)

        rows = (await db.execute(stmt)).scalars().all()

        ranked_rows = []
        for row in rows:
            type_code = (
                getattr(row, target.doc_type_attr) if target.doc_type_attr else target.type_code
            ) or target.type_code
            if external_allowed is not None:
                if type_code not in external_allowed.get(row.project_id, set()):
                    continue
            doc_id = getattr(row, target.id_attr)
            title = getattr(row, target.title_attr)
            project = projects[row.project_id]
            rank = rank_match(query_lower, doc_id, title)
            ranked_rows.append(
                (
                    rank,
                    SearchResultItem(
                        type=type_code,
                        id=row.id,
                        doc_id=doc_id,
                        title=title or "",
                        status=getattr(row, "status", None),
                        project_id=row.project_id,
                        project_prefix=project.prefix,
                        project_name=project.name,
                    ),
                )
            )

        ranked_rows.sort(key=lambda pair: (pair[0], pair[1].doc_id or "", pair[1].id))
        candidates.extend(ranked_rows[:PER_TYPE_LIMIT])

    candidates.sort(key=lambda pair: (pair[0], pair[1].type, pair[1].doc_id or ""))
    items = [item for _, item in candidates[:limit]]
    return SearchResponse(query=q, total=len(items), items=items)


@router.get("", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=MIN_QUERY_LENGTH, max_length=200),
    project_id: Optional[int] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await run_global_search(db, current_user, q=q, project_id=project_id, limit=limit)
