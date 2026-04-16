"""
Unified docs facade: Polarion-style lookup by string doc_id across all type tables,
and a unified list endpoint for all doc types within a project.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, union_all, literal_column, String, cast, or_
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import (
    Project, Requirement, TestCase, Document, DesignItem,
    RiskItem, ChangeRequest, TestConcept,
)
from app.models.user import User
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class DocShellResponse(BaseModel):
    id: int
    doc_id: str
    doc_type: str
    title: str
    status: str
    priority: str | None = None
    project_id: int
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
        result = await db.execute(
            select(Project).where(Project.prefix == identifier.upper())
        )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


TYPE_MAP = {
    "REQ": (Requirement, "req_id", "requirements"),
    "TC": (TestCase, "tc_id", "test_cases"),
    "DOC": (Document, "doc_id", "documents"),
    "DES": (DesignItem, "design_id", "design_items"),
    "RSK": (RiskItem, "risk_id", "risk_items"),
    "CHG": (ChangeRequest, "change_id", "change_requests"),
    "TCO": (TestConcept, "concept_id", "test_concepts"),
}


def _get_priority(model, row):
    """Extract priority from a model row, handling models without a priority column."""
    if hasattr(model, 'priority'):
        return row.priority
    if hasattr(model, 'severity'):
        return row.severity
    return None


@router.get("/projects/{project_ref}/docs", response_model=List[DocShellResponse])
async def list_all_docs(
    project_ref: str,
    type: Optional[List[str]] = Query(None),
    status: Optional[str] = None,
    q: Optional[str] = None,
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
        title_col = model.title if hasattr(model, 'title') else model.name

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

        for row in rows:
            doc_id_val = getattr(row, id_col_name)
            title_val = row.title if hasattr(row, 'title') else row.name
            results.append(DocShellResponse(
                id=row.id,
                doc_id=doc_id_val or f"{type_code}-{row.id}",
                doc_type=type_code,
                title=title_val,
                status=row.status,
                priority=_get_priority(model, row),
                project_id=project.id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            ))

    results.sort(key=lambda r: r.updated_at, reverse=True)
    return results


@router.get("/projects/{project_ref}/docs/{doc_id_str}", response_model=DocDetailFacadeResponse)
async def get_doc_by_string_id(
    project_ref: str,
    doc_id_str: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Look up a doc by its human-readable string ID (e.g. PRJ-REQ-001) across all type tables."""
    project = await resolve_project(db, project_ref)

    for type_code, (model, id_col_name, _table) in TYPE_MAP.items():
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
            title_val = row.title if hasattr(row, 'title') else row.name
            desc_val = row.description if hasattr(row, 'description') else None
            cj = row.content_json if hasattr(row, 'content_json') else None
            ch = row.content_html if hasattr(row, 'content_html') else None

            return DocDetailFacadeResponse(
                id=row.id,
                doc_id=doc_id_val,
                doc_type=type_code,
                title=title_val,
                status=row.status,
                priority=_get_priority(model, row),
                project_id=project.id,
                description=desc_val,
                content_json=cj,
                content_html=ch,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    raise HTTPException(status_code=404, detail=f"Document '{doc_id_str}' not found in project '{project.prefix}'")
