"""Server-side exports: requirement specifications and traceability, as CSV/PDF."""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import (
    VERIFY_LINK_ROLE,
    VERIFY_SOURCE_TYPE,
    VERIFY_TARGET_TYPE,
)
from app.core.database import get_db
from app.core.security import require_project_access, require_role
from app.models import ArtefactLink, Project, Requirement, TestCase
from app.models.user import User, UserRole

router = APIRouter()

CSV_MEDIA_TYPE = "text/csv; charset=utf-8"


async def _load_project(db: AsyncSession, project_id: int, current_user: User) -> Project:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await require_project_access(
        db, current_user, project_id, roles={UserRole.admin.value, UserRole.maintainer.value}
    )
    return project


async def _load_requirements(db: AsyncSession, project_id: int) -> list[Requirement]:
    return (
        (
            await db.execute(
                select(Requirement)
                .where(Requirement.project_id == project_id)
                .order_by(Requirement.req_id)
            )
        )
        .scalars()
        .all()
    )


def _csv_response(rows: list[list], header: list[str], filename: str) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        content=buffer.getvalue(),
        media_type=CSV_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _pdf_safe(text: str) -> str:
    """fpdf's built-in fonts are latin-1; degrade anything outside it."""
    return (text or "").encode("latin-1", "replace").decode("latin-1")


def _requirements_pdf(project: Project, requirements: list[Requirement]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(
        0,
        12,
        _pdf_safe(f"{project.name} - Requirements Specification"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.multi_cell(
        0,
        7,
        _pdf_safe(f"Project {project.prefix} - generated {generated}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.multi_cell(
        0, 7, _pdf_safe(f"{len(requirements)} requirement(s)"), new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(4)

    for req in requirements:
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, _pdf_safe(f"{req.req_id}  {req.title}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 9)
        meta = (
            f"status: {req.status} | priority: {req.priority} | "
            f"type: {req.req_type} | origin: {req.req_origin}"
        )
        pdf.multi_cell(0, 5, _pdf_safe(meta), new_x="LMARGIN", new_y="NEXT")
        if req.description:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, _pdf_safe(req.description), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    return bytes(pdf.output())


@router.get("/projects/{project_id}/export/requirements")
async def export_requirements(
    project_id: int,
    format: str = Query(default="csv", pattern="^(csv|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """Export the project's requirements as CSV or a PDF specification."""
    project = await _load_project(db, project_id, current_user)
    requirements = await _load_requirements(db, project_id)

    if format == "pdf":
        content = _requirements_pdf(project, requirements)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{project.prefix}-requirements.pdf"'
            },
        )

    id_by_pk = {r.id: r.req_id for r in requirements}
    rows = [
        [
            r.req_id,
            r.title,
            r.status,
            r.priority,
            r.req_type,
            r.req_origin,
            r.visibility,
            id_by_pk.get(r.parent_id, "") if r.parent_id else "",
            r.description or "",
            r.created_at.isoformat() if r.created_at else "",
            r.updated_at.isoformat() if r.updated_at else "",
        ]
        for r in requirements
    ]
    header = [
        "req_id",
        "title",
        "status",
        "priority",
        "type",
        "origin",
        "visibility",
        "parent_req_id",
        "description",
        "created_at",
        "updated_at",
    ]
    return _csv_response(rows, header, f"{project.prefix}-requirements.csv")


@router.get("/projects/{project_id}/export/traceability")
async def export_traceability(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """Export the requirement <-> verifying-test-case matrix as CSV.

    Long format: one row per (requirement, verifying test case) pair; uncovered
    requirements appear once with empty test-case columns so coverage gaps are
    visible in the same file.
    """
    project = await _load_project(db, project_id, current_user)
    requirements = await _load_requirements(db, project_id)

    link_rows = (
        await db.execute(
            select(ArtefactLink.target_id, TestCase)
            .join(TestCase, TestCase.id == ArtefactLink.source_id)
            .where(
                ArtefactLink.project_id == project_id,
                ArtefactLink.role == VERIFY_LINK_ROLE,
                ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
                ArtefactLink.target_type == VERIFY_TARGET_TYPE,
            )
            .order_by(TestCase.tc_id)
        )
    ).all()

    tcs_by_req: dict[int, list[TestCase]] = {}
    for req_pk, tc in link_rows:
        tcs_by_req.setdefault(req_pk, []).append(tc)

    rows: list[list] = []
    for req in requirements:
        verifying = tcs_by_req.get(req.id, [])
        if not verifying:
            rows.append([req.req_id, req.title, req.status, "no", "", "", ""])
            continue
        for tc in verifying:
            rows.append(
                [
                    req.req_id,
                    req.title,
                    req.status,
                    "yes",
                    tc.tc_id,
                    tc.title,
                    tc.last_execution_status or "",
                ]
            )

    header = [
        "req_id",
        "req_title",
        "req_status",
        "covered",
        "tc_id",
        "tc_title",
        "tc_last_execution",
    ]
    return _csv_response(rows, header, f"{project.prefix}-traceability.csv")
