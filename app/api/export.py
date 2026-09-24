"""Server-side exports: requirements, traceability, test cases and the verification dossier.

Every export reads the same rows the user may see in the app: artefacts an external
user may not see and document types outside their allowlist are never included.
"""

import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from fpdf import FPDF
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import (
    VERIFY_LINK_ROLE,
    VERIFY_SOURCE_TYPE,
    VERIFY_TARGET_TYPE,
)
from app.core.database import get_db
from app.core.security import (
    apply_external_visibility_filter,
    get_current_user,
    require_external_doc_type_access,
    require_project_access,
)
from app.models import (
    ArtefactLink,
    CompanyLogo,
    Project,
    Requirement,
    TestCase,
    TestRunLink,
)
from app.models.user import User
from app.services.audit import record_audit_event

router = APIRouter()

CSV_MEDIA_TYPE = "text/csv; charset=utf-8"

# Report letterhead assets. The Bloom mark and the EmbedLabs footer are shipped
# with the app; the customer's own logo is uploaded and passed in at render time.
ASSETS = Path(__file__).resolve().parent.parent / "assets"
BLOOM_LOGO = ASSETS / "bloom-logo.png"
EMBEDLABS_LOGO = ASSETS / "embedlabs-logo.png"
EMBEDLABS_URL = "https://www.embedlabs.net"
from app.core.tc_steps import has_precondition_rows, rows_to_text


def _fit(iw: int, ih: int, max_w: float, max_h: float) -> tuple[float, float]:
    """Scale (iw, ih) to fit inside the box, keeping aspect ratio (never cropped)."""
    if iw <= 0 or ih <= 0:
        return max_w, max_h
    scale = min(max_w / iw, max_h / ih)
    return iw * scale, ih * scale


class _BrandedPDF(FPDF):
    """A4 report letterhead: the customer's company logo top-left, the Bloom
    application mark top-right, and the EmbedLabs tamper-evidence footer -
    "Powered by EmbedLabs", linked - on every page. The EmbedLabs branding is
    deployment-agnostic and always present; the company logo is optional."""

    def __init__(self, *args, company_logo: bytes | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._company_logo = company_logo

    def header(self) -> None:
        top = 9
        # Customer company logo, top-left, fit inside a fixed box so a wide or
        # tall logo can never be cropped or pushed off the page edge.
        if self._company_logo:
            try:
                with Image.open(io.BytesIO(self._company_logo)) as im:
                    w, h = _fit(im.width, im.height, 55, 15)
                self.image(io.BytesIO(self._company_logo), x=self.l_margin, y=top, w=w, h=h)
            except Exception:  # noqa: BLE001 - a bad logo must never break the report
                pass
        # Bloom application mark, top-right.
        if BLOOM_LOGO.exists():
            try:
                with Image.open(BLOOM_LOGO) as im:
                    w, h = _fit(im.width, im.height, 42, 12)
                self.image(str(BLOOM_LOGO), x=self.w - self.r_margin - w, y=top, w=w, h=h)
            except Exception:  # noqa: BLE001
                pass

    def footer(self) -> None:
        self.set_y(-14)
        self.set_draw_color(0xC7, 0xCD, 0xD6)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1.5)
        y = self.get_y()
        x = self.l_margin
        if EMBEDLABS_LOGO.exists():
            try:
                with Image.open(EMBEDLABS_LOGO) as im:
                    w, h = _fit(im.width, im.height, 30, 4.5)
                self.image(str(EMBEDLABS_LOGO), x=x, y=y + (5 - h) / 2, w=w, h=h)
                x += w + 2
            except Exception:  # noqa: BLE001
                pass
        self.set_xy(x, y)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(0x25, 0x63, 0xEB)
        label = "Powered by EmbedLabs"
        self.cell(self.get_string_width(label) + 1, 5, label, link=EMBEDLABS_URL)
        # Page number, bottom-right, on the same baseline.
        self.set_text_color(0x64, 0x74, 0x8B)
        self.set_xy(self.l_margin, y)
        self.cell(0, 5, f"Page {self.page_no()}", align="R")


async def _load_project(
    db: AsyncSession, project_id: int, current_user: User, resource: str
) -> Project:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await require_project_access(db, current_user, project_id, permission=("export", resource))
    return project


async def _load_requirements(
    db: AsyncSession, project_id: int, current_user: User
) -> list[Requirement]:
    """The project's requirements this user may see, ordered by their human id."""
    await require_external_doc_type_access(db, current_user, project_id, "REQ")
    query = (
        select(Requirement).where(Requirement.project_id == project_id).order_by(Requirement.req_id)
    )
    query = apply_external_visibility_filter(query, Requirement, current_user)
    return (await db.execute(query)).scalars().all()


async def _verifying_test_cases(
    db: AsyncSession, project_id: int, current_user: User
) -> dict[int, list[TestCase]]:
    """The test cases this user may see that verify each requirement, by requirement id."""
    await require_external_doc_type_access(db, current_user, project_id, "TC")
    query = (
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
    query = apply_external_visibility_filter(query, TestCase, current_user)
    tcs_by_req: dict[int, list[TestCase]] = {}
    for req_pk, tc in (await db.execute(query)).all():
        tcs_by_req.setdefault(req_pk, []).append(tc)
    return tcs_by_req


def _pdf_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _report_start(logo: bytes | None, title: str, project: Project, summary: str) -> "_BrandedPDF":
    """A new branded report with its title, project, generation time and summary line."""
    pdf = _BrandedPDF(company_logo=logo)
    pdf.set_top_margin(28)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(0, 12, _pdf_safe(f"{project.name} - {title}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.multi_cell(
        0,
        7,
        _pdf_safe(f"Project {project.prefix} - generated {generated}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.multi_cell(0, 7, _pdf_safe(summary), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    return pdf


def _line(pdf: "_BrandedPDF", text: str, style: str = "", size: int = 10, height: int = 5) -> None:
    pdf.set_font("Helvetica", style, size)
    pdf.multi_cell(0, height, _pdf_safe(text), new_x="LMARGIN", new_y="NEXT")


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
    row = (await db.execute(select(CompanyLogo).limit(1))).scalar_one_or_none()
    return row.logo if row and row.logo else None


def _requirements_pdf(
    project: Project, requirements: list[Requirement], logo: bytes | None = None
) -> bytes:
    pdf = _report_start(
        logo, "Requirements Specification", project, f"{len(requirements)} requirement(s)"
    )

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


def _traceability_pdf(
    project: Project,
    requirements: list[Requirement],
    tcs_by_req: dict[int, list[TestCase]],
    logo: bytes | None = None,
) -> bytes:
    """The requirement to verifying test case matrix, with coverage."""
    covered = sum(1 for req in requirements if tcs_by_req.get(req.id))
    pdf = _report_start(
        logo,
        "Traceability Matrix",
        project,
        f"{len(requirements)} requirement(s), {covered} covered by a test case",
    )
    for req in requirements:
        _line(pdf, f"{req.req_id}  {req.title}", "B", 11, 6)
        verifying = tcs_by_req.get(req.id, [])
        if not verifying:
            _line(pdf, "Not covered by a test case", "I", 9)
        for tc in verifying:
            _line(
                pdf,
                f"    {tc.tc_id}  {tc.title}  -  {tc.last_execution_status or 'not run'}",
                "",
                9,
            )
        pdf.ln(2)
    return bytes(pdf.output())


def _test_cases_pdf(
    project: Project, test_cases: list[TestCase], logo: bytes | None = None
) -> bytes:
    """The test cases with their preconditions, steps and last result."""
    pdf = _report_start(logo, "Test Cases", project, f"{len(test_cases)} test case(s)")
    for tc in test_cases:
        _line(pdf, f"{tc.tc_id}  {tc.title}", "B", 12, 7)
        _line(
            pdf,
            f"status: {tc.status} | last result: {tc.last_execution_status or 'not run'}",
            "I",
            9,
        )
        if tc.description:
            _line(pdf, tc.description)
        if tc.preconditions and not has_precondition_rows(tc.steps):
            _line(pdf, f"Pre-Condition: {tc.preconditions}")
        steps = rows_to_text(tc.steps)
        if steps:
            _line(pdf, steps, "", 9)
        pdf.ln(3)
    return bytes(pdf.output())


def _dossier_pdf(
    project: Project,
    requirements: list[Requirement],
    tcs_by_req: dict[int, list[TestCase]],
    runs_by_req: dict[int, list[TestRunLink]],
    logo: bytes | None = None,
) -> bytes:
    """Each requirement with the test cases that verify it, their results and linked runs."""
    covered = sum(1 for req in requirements if tcs_by_req.get(req.id))
    passed = sum(
        1
        for req in requirements
        if tcs_by_req.get(req.id)
        and all(tc.last_execution_status == "Passed" for tc in tcs_by_req[req.id])
    )
    pdf = _report_start(
        logo,
        "Verification Dossier",
        project,
        f"{len(requirements)} requirement(s), {covered} covered, {passed} verified by passing tests",
    )
    for req in requirements:
        _line(pdf, f"{req.req_id}  {req.title}", "B", 12, 7)
        _line(pdf, f"status: {req.status} | priority: {req.priority}", "I", 9)
        verifying = tcs_by_req.get(req.id, [])
        if not verifying:
            _line(pdf, "No verifying test case.", "", 9)
        for tc in verifying:
            executed = tc.last_executed_at.strftime("%Y-%m-%d") if tc.last_executed_at else "never"
            _line(
                pdf,
                f"  {tc.tc_id}  {tc.title}: {tc.last_execution_status or 'not run'} (last run {executed})",
                "",
                9,
            )
        for run in runs_by_req.get(req.id, []):
            _line(
                pdf,
                f"  Run {run.test_run_id} {run.test_run_name or ''}: {run.status or 'unknown'}",
                "",
                9,
            )
        pdf.ln(3)
    return bytes(pdf.output())


@router.get("/projects/{project_id}/export/requirements")
async def export_requirements(
    project_id: int,
    format: str = Query(default="csv", pattern="^(csv|pdf)$"),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Export the project's requirements as CSV or a PDF specification."""
    project = await _load_project(db, project_id, current_user, "requirement")
    await record_audit_event(
        db,
        "export.generated",
        target_type="project",
        target_id=project.id,
        project_id=project.id,
        details={"kind": "requirements", "format": format},
    )
    requirements = await _load_requirements(db, project_id, current_user)

    if format == "pdf":
        content = _requirements_pdf(project, requirements, await _load_report_logo(db))
        return _pdf_response(content, f"{project.prefix}-requirements.pdf")

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
    format: str = Query(default="csv", pattern="^(csv|pdf)$"),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Export the requirement <-> verifying-test-case matrix as CSV or PDF."""
    project = await _load_project(db, project_id, current_user, "requirement")
    await record_audit_event(
        db,
        "export.generated",
        target_type="project",
        target_id=project.id,
        project_id=project.id,
        details={"kind": "traceability", "format": format},
    )
    requirements = await _load_requirements(db, project_id, current_user)
    tcs_by_req = await _verifying_test_cases(db, project_id, current_user)

    if format == "pdf":
        content = _traceability_pdf(project, requirements, tcs_by_req, await _load_report_logo(db))
        return _pdf_response(content, f"{project.prefix}-traceability.pdf")

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


async def _load_test_cases(db: AsyncSession, project_id: int, current_user: User) -> list[TestCase]:
    """The project's test cases this user may see, ordered by their human id."""
    await require_external_doc_type_access(db, current_user, project_id, "TC")
    query = select(TestCase).where(TestCase.project_id == project_id).order_by(TestCase.tc_id)
    query = apply_external_visibility_filter(query, TestCase, current_user)
    return (await db.execute(query)).scalars().all()


def _test_cases_markdown(project: Project, test_cases: list[TestCase]) -> str:
    """Render the test cases in the Markdown import format, so the file re-imports."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        f"Test cases of {project.name} ({project.prefix}), exported {generated}, "
        f"{len(test_cases)} test case(s).",
        "",
    ]
    for tc in test_cases:
        parts.extend([f"## [TC] {tc.title}", ""])
        if tc.description:
            parts.extend([tc.description, ""])
        rows = []
        if tc.preconditions and not has_precondition_rows(tc.steps):
            rows.append(f"- Pre-Condition: {tc.preconditions}")
        steps = rows_to_text(tc.steps)
        if steps:
            rows.append(steps)
        if rows:
            parts.extend([*rows, ""])
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
        ET.SubElement(node, "steps").text = rows_to_text(tc.steps)
        ET.SubElement(node, "description").text = tc.description or ""
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


@router.get("/projects/{project_id}/export/test-cases")
async def export_test_cases(
    project_id: int,
    format: str = Query(default="csv", pattern="^(csv|md|xml|pdf)$"),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Export the project's test cases as CSV, Markdown, XML or PDF."""
    project = await _load_project(db, project_id, current_user, "test_case")
    await record_audit_event(
        db,
        "export.generated",
        target_type="project",
        target_id=project.id,
        project_id=project.id,
        details={"kind": "test_cases", "format": format},
    )
    test_cases = await _load_test_cases(db, project_id, current_user)

    if format == "pdf":
        content = _test_cases_pdf(project, test_cases, await _load_report_logo(db))
        return _pdf_response(content, f"{project.prefix}-test-cases.pdf")
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
            rows_to_text(tc.steps),
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


@router.get("/projects/{project_id}/export/verification-dossier")
async def export_verification_dossier(
    project_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Export the verification dossier: requirements, verifying test cases, results and runs."""
    project = await _load_project(db, project_id, current_user, "requirement")
    await require_project_access(db, current_user, project_id, permission=("export", "test_case"))
    await record_audit_event(
        db,
        "export.generated",
        target_type="project",
        target_id=project.id,
        project_id=project.id,
        details={"kind": "verification_dossier", "format": "pdf"},
    )
    requirements = await _load_requirements(db, project_id, current_user)
    tcs_by_req = await _verifying_test_cases(db, project_id, current_user)
    runs_by_req: dict[int, list[TestRunLink]] = {}
    if requirements:
        run_rows = (
            (
                await db.execute(
                    select(TestRunLink)
                    .where(TestRunLink.requirement_id.in_([req.id for req in requirements]))
                    .order_by(TestRunLink.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        for run in run_rows:
            runs_by_req.setdefault(run.requirement_id, []).append(run)
    content = _dossier_pdf(
        project, requirements, tcs_by_req, runs_by_req, await _load_report_logo(db)
    )
    return _pdf_response(content, f"{project.prefix}-verification-dossier.pdf")
