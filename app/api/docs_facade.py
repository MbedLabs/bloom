"""
Unified docs facade: Polarion-style lookup by string doc_id across all type tables,
and a unified list endpoint for all doc types within a project.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.document_kinds import (
    CANONICAL_DOCUMENT_KINDS,
    document_kind_from_slug,
    normalize_document_kind,
)
from app.core.security import get_current_user
from app.models import (
    ArtefactLink,
    ChangeRequest,
    DesignItem,
    Document,
    Project,
    Requirement,
    RiskItem,
    TestCase,
    TestConcept,
)
from app.models.user import User

router = APIRouter()


class DocShellResponse(BaseModel):
    id: int
    doc_id: str
    doc_type: str
    title: str
    status: str
    priority: str | None = None
    project_id: int
    reviewer_id: int | None = None
    incoming_links: int = 0
    outgoing_links: int = 0
    suspect_links: int = 0
    created_at: datetime
    updated_at: datetime


class DocDetailFacadeResponse(DocShellResponse):
    description: str | None = None
    content_json: dict | None = None
    content_html: str | None = None


async def resolve_project(db: AsyncSession, identifier: str) -> Project:
    """Resolve a project by numeric ID or string prefix."""
    if identifier.isdigit():
        result = await db.execute(select(Project).where(Project.id == int(identifier)))
    else:
        result = await db.execute(select(Project).where(Project.prefix == identifier.upper()))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


TYPE_MAP = {
    "REQ": (Requirement, "req_id", "requirements"),
    "TC": (TestCase, "tc_id", "test-cases"),
    "DES": (DesignItem, "design_id", "designs"),
    "RSK": (RiskItem, "risk_id", "risks"),
    "CHG": (ChangeRequest, "change_id", "changes"),
    "TCO": (TestConcept, "concept_id", "test-concepts"),
}

LEGACY_TYPE_SLUG_ALIASES = {
    "test_cases": "test-cases",
    "design_items": "designs",
    "risk_items": "risks",
    "change_requests": "changes",
    "test_concepts": "test-concepts",
}


def _get_priority(model, row):
    """Extract priority from a model row, handling models without a priority column."""
    if hasattr(model, "priority"):
        return row.priority
    if hasattr(model, "severity"):
        return row.severity
    return None


def _get_reviewer_id(model, row) -> int | None:
    """Extract reviewer_id from a model row, if the column exists."""
    return getattr(row, "reviewer_id", None)


def _resolved_doc_type(type_code: str, row) -> str:
    """Resolve a facade doc_type for generic Document rows."""
    if type_code == "DOCUMENT":
        return normalize_document_kind(getattr(row, "doc_type", None))
    return type_code


async def _count_links(
    db: AsyncSession, project_id: int, type_code: str, row_ids: list[int]
) -> dict[int, dict]:
    """Return {row_id: {incoming, outgoing, suspect}} for the given rows."""
    if not row_ids:
        return {}
    incoming_q = (
        select(
            ArtefactLink.target_id,
            func.count().label("cnt"),
            func.sum(case((ArtefactLink.suspect == True, 1), else_=0)).label("suspect_cnt"),
        )
        .where(
            ArtefactLink.project_id == project_id,
            ArtefactLink.target_type == type_code,
            ArtefactLink.target_id.in_(row_ids),
        )
        .group_by(ArtefactLink.target_id)
    )
    outgoing_q = (
        select(
            ArtefactLink.source_id,
            func.count().label("cnt"),
            func.sum(case((ArtefactLink.suspect == True, 1), else_=0)).label("suspect_cnt"),
        )
        .where(
            ArtefactLink.project_id == project_id,
            ArtefactLink.source_type == type_code,
            ArtefactLink.source_id.in_(row_ids),
        )
        .group_by(ArtefactLink.source_id)
    )
    incoming_rows = (await db.execute(incoming_q)).all()
    outgoing_rows = (await db.execute(outgoing_q)).all()
    result: dict[int, dict] = {rid: {"incoming": 0, "outgoing": 0, "suspect": 0} for rid in row_ids}
    for target_id, cnt, suspect_cnt in incoming_rows:
        if target_id in result:
            result[target_id]["incoming"] = cnt
            result[target_id]["suspect"] = suspect_cnt
    for source_id, cnt, suspect_cnt in outgoing_rows:
        if source_id in result:
            result[source_id]["outgoing"] = cnt
            result[source_id]["suspect"] += suspect_cnt or 0
    return result


@router.get("/projects/{project_ref}/docs", response_model=List[DocShellResponse])
async def list_all_docs(
    project_ref: str,
    type: Optional[List[str]] = Query(None),
    status: Optional[str] = None,
    q: Optional[str] = None,
    include_link_counts: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List all docs across all types for a project."""
    project = await resolve_project(db, project_ref)
    results = []

    type_filter = [t.upper() for t in type] if type else None

    for type_code, (model, id_col_name, _table) in TYPE_MAP.items():
        if type_filter and type_code not in type_filter:
            continue

        id_col = getattr(model, id_col_name)
        title_col = model.title if hasattr(model, "title") else model.name

        query = select(model).where(model.project_id == project.id)

        if status:
            query = query.where(model.status == status)
        if q:
            query = query.where(
                or_(
                    title_col.ilike(f"%{q}%"),
                    id_col.ilike(f"%{q}%"),
                )
            )

        rows = (await db.execute(query.order_by(model.created_at.desc()))).scalars().all()
        row_ids = [row.id for row in rows]
        link_counts = (
            await _count_links(db, project.id, type_code, row_ids) if include_link_counts else {}
        )

        for row in rows:
            doc_id_val = getattr(row, id_col_name)
            title_val = row.title if hasattr(row, "title") else row.name
            lc = link_counts.get(row.id, {"incoming": 0, "outgoing": 0, "suspect": 0})
            results.append(
                DocShellResponse(
                    id=row.id,
                    doc_id=doc_id_val or f"{type_code}-{row.id}",
                    doc_type=type_code,
                    title=title_val,
                    status=row.status,
                    priority=_get_priority(model, row),
                    project_id=project.id,
                    reviewer_id=_get_reviewer_id(model, row),
                    incoming_links=lc["incoming"],
                    outgoing_links=lc["outgoing"],
                    suspect_links=lc["suspect"],
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )

    document_type_filter = (
        [t for t in type_filter if t in CANONICAL_DOCUMENT_KINDS]
        if type_filter
        else list(CANONICAL_DOCUMENT_KINDS)
    )
    if document_type_filter:
        document_query = select(Document).where(
            Document.project_id == project.id,
            Document.doc_type.in_(document_type_filter),
        )
        if status:
            document_query = document_query.where(Document.status == status)
        if q:
            document_query = document_query.where(
                or_(
                    Document.title.ilike(f"%{q}%"),
                    Document.doc_id.ilike(f"%{q}%"),
                )
            )

        document_rows = (
            (await db.execute(document_query.order_by(Document.created_at.desc()))).scalars().all()
        )
        grouped_row_ids: dict[str, list[int]] = {}
        for row in document_rows:
            grouped_row_ids.setdefault(normalize_document_kind(row.doc_type), []).append(row.id)
        link_counts_by_type = (
            {
                doc_type: await _count_links(db, project.id, doc_type, row_ids)
                for doc_type, row_ids in grouped_row_ids.items()
            }
            if include_link_counts
            else {}
        )

        for row in document_rows:
            doc_type = normalize_document_kind(row.doc_type)
            lc = link_counts_by_type.get(doc_type, {}).get(
                row.id,
                {"incoming": 0, "outgoing": 0, "suspect": 0},
            )
            results.append(
                DocShellResponse(
                    id=row.id,
                    doc_id=row.doc_id or f"{doc_type}-{row.id}",
                    doc_type=doc_type,
                    title=row.title,
                    status=row.status,
                    priority=_get_priority(Document, row),
                    project_id=project.id,
                    reviewer_id=_get_reviewer_id(Document, row),
                    incoming_links=lc["incoming"],
                    outgoing_links=lc["outgoing"],
                    suspect_links=lc["suspect"],
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )

    results.sort(key=lambda r: r.updated_at, reverse=True)
    return results


@router.get(
    "/projects/{project_ref}/docs/{kind_slug}/{doc_id_str}", response_model=DocDetailFacadeResponse
)
async def get_doc_by_kind_and_string_id(
    project_ref: str,
    kind_slug: str,
    doc_id_str: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Look up a doc by its kind-aware slug and human-readable string ID."""
    project = await resolve_project(db, project_ref)
    kind_slug = LEGACY_TYPE_SLUG_ALIASES.get(kind_slug, kind_slug)
    requested_kind = None
    if kind_slug in {slug for _, (_, _, slug) in TYPE_MAP.items()}:
        pass
    else:
        requested_kind = document_kind_from_slug(kind_slug)

    if requested_kind in CANONICAL_DOCUMENT_KINDS:
        result = await db.execute(
            select(Document).where(
                Document.project_id == project.id,
                Document.doc_type == requested_kind,
                Document.doc_id == doc_id_str,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            link_data = (await _count_links(db, project.id, requested_kind, [row.id])).get(
                row.id, {"incoming": 0, "outgoing": 0, "suspect": 0}
            )
            return DocDetailFacadeResponse(
                id=row.id,
                doc_id=row.doc_id,
                doc_type=requested_kind,
                title=row.title,
                status=row.status,
                priority=_get_priority(Document, row),
                project_id=project.id,
                reviewer_id=_get_reviewer_id(Document, row),
                incoming_links=link_data["incoming"],
                outgoing_links=link_data["outgoing"],
                suspect_links=link_data["suspect"],
                description=row.description,
                content_json=row.content_json,
                content_html=row.content_html,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
    else:
        for type_code, (model, id_col_name, slug) in TYPE_MAP.items():
            if slug != kind_slug:
                continue

            id_col = getattr(model, id_col_name)
            result = await db.execute(
                select(model).where(
                    model.project_id == project.id,
                    id_col == doc_id_str,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                doc_id_val = getattr(row, id_col_name)
                title_val = row.title if hasattr(row, "title") else row.name
                desc_val = row.description if hasattr(row, "description") else None
                cj = row.content_json if hasattr(row, "content_json") else None
                ch = row.content_html if hasattr(row, "content_html") else None
                resolved_type = _resolved_doc_type(type_code, row)
                lc = await _count_links(db, project.id, resolved_type, [row.id])
                link_data = lc.get(row.id, {"incoming": 0, "outgoing": 0, "suspect": 0})

                return DocDetailFacadeResponse(
                    id=row.id,
                    doc_id=doc_id_val,
                    doc_type=resolved_type,
                    title=title_val,
                    status=row.status,
                    priority=_get_priority(model, row),
                    project_id=project.id,
                    reviewer_id=_get_reviewer_id(model, row),
                    incoming_links=link_data["incoming"],
                    outgoing_links=link_data["outgoing"],
                    suspect_links=link_data["suspect"],
                    description=desc_val,
                    content_json=cj,
                    content_html=ch,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )

    raise HTTPException(
        status_code=404,
        detail=(
            f"Document '{doc_id_str}' with kind '{kind_slug}' "
            f"not found in project '{project.prefix}'"
        ),
    )
