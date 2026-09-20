"""Server-side exports: requirement specifications and traceability, as CSV/PDF."""

import csv
import io
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

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
from app.models import ArtefactLink, Project, ReportBranding, Requirement, TestCase
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


async def _load_report_logo(db: AsyncSession):
    row = (await db.execute(select(ReportBranding).limit(1))).scalar_one_or_none()
    return row.logo if row and row.logo else None


def _requirements_pdf(
    project: Project, requirements: list[Requirement], logo: bytes | None = None
) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    if logo:
        try:
            pdf.image(io.BytesIO(logo), x=170, y=8, h=16)
        except Exception:  # noqa: BLE001 - a bad logo must never break the report
            pass

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
        content = _requirements_pdf(project, requirements, await _load_report_logo(db))
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
    """Export the requirement <-> verifying-test-case matrix as CSV."""
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


async def _load_test_cases(db: AsyncSession, project_id: int) -> list[TestCase]:
    """Load a project's test cases ordered by their human id."""
    return (
        (
            await db.execute(
                select(TestCase).where(TestCase.project_id == project_id).order_by(TestCase.tc_id)
            )
        )
        .scalars()
        .all()
    )


def _steps_to_text(steps) -> str:
    """Flatten a test case's steps JSON into readable plain text."""
    if not steps:
        return ""
    if isinstance(steps, dict):
        inner = steps.get("steps")
        if isinstance(inner, list):
            return _steps_to_text(inner)
        return "\n".join(f"{key}: {value}" for key, value in steps.items())
    if isinstance(steps, list):
        lines = []
        for index, step in enumerate(steps, start=1):
            if isinstance(step, dict):
                action = step.get("action") or step.get("step") or ""
                expected = step.get("expected") or step.get("expected_result") or ""
                line = f"{index}. {action}".rstrip()
                if expected:
                    line = f"{line} => {expected}"
                lines.append(line)
            else:
                lines.append(f"{index}. {step}")
        return "\n".join(lines)
    return str(steps)


def _test_cases_markdown(project: Project, test_cases: list[TestCase]) -> str:
    """Render the test cases as a Markdown document."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        f"# {project.name} - Test Cases",
        "",
        f"Project {project.prefix} - generated {generated} - {len(test_cases)} test case(s)",
        "",
    ]
    for tc in test_cases:
        parts.append(f"## {tc.tc_id}  {tc.title}")
        parts.append("")
        parts.append(f"- **Status:** {tc.status}")
        parts.append(f"- **Visibility:** {tc.visibility}")
        if tc.last_execution_status:
            parts.append(f"- **Last execution:** {tc.last_execution_status}")
        parts.append("")
        if tc.preconditions:
            parts.extend(["**Preconditions**", "", tc.preconditions, ""])
        steps = _steps_to_text(tc.steps)
        if steps:
            parts.extend(["**Steps**", "", steps, ""])
        if tc.description:
            parts.extend([tc.description, ""])
    return "\n".join(parts).rstrip() + "\n"


def _test_cases_xml(project: Project, test_cases: list[TestCase]) -> bytes:
    """Render the test cases as an XML document."""
    root = ET.Element(
        "test-cases",
        {
            "project": project.prefix,
            "name": project.name,
            "generated": datetime.now(timezone.utc).isoformat(),
            "count": str(len(test_cases)),
        },
    )
    for tc in test_cases:
        node = ET.SubElement(root, "test-case", {"id": tc.tc_id})
        ET.SubElement(node, "title").text = tc.title or ""
        ET.SubElement(node, "status").text = tc.status or ""
        ET.SubElement(node, "visibility").text = tc.visibility or ""
        ET.SubElement(node, "preconditions").text = tc.preconditions or ""
        ET.SubElement(node, "steps").text = _steps_to_text(tc.steps)
        ET.SubElement(node, "description").text = tc.description or ""
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


@router.get("/projects/{project_id}/export/test-cases")
async def export_test_cases(
    project_id: int,
    format: str = Query(default="csv", pattern="^(csv|md|xml)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """Export the project's test cases as CSV, Markdown or XML."""
    project = await _load_project(db, project_id, current_user)
    test_cases = await _load_test_cases(db, project_id)

    if format == "md":
        return Response(
            content=_test_cases_markdown(project, test_cases),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{project.prefix}-test-cases.md"'
            },
        )
    if format == "xml":
        return Response(
            content=_test_cases_xml(project, test_cases),
            media_type="application/xml; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{project.prefix}-test-cases.xml"'
            },
        )

    rows = [
        [
            tc.tc_id,
            tc.title,
            tc.status,
            tc.visibility,
            tc.preconditions or "",
            _steps_to_text(tc.steps),
            tc.description or "",
            tc.last_execution_status or "",
            tc.created_at.isoformat() if tc.created_at else "",
            tc.updated_at.isoformat() if tc.updated_at else "",
        ]
        for tc in test_cases
    ]
    header = [
        "tc_id",
        "title",
        "status",
        "visibility",
        "preconditions",
        "steps",
        "description",
        "last_execution",
        "created_at",
        "updated_at",
    ]
    return _csv_response(rows, header, f"{project.prefix}-test-cases.csv")
