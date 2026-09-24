"""
Cross-project import service for docs (REQ/TC).
"""

import csv
import functools
import io
import json
import re
from typing import Dict, List, Optional

from defusedxml import ElementTree as SafeET
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import log_artefact_activity
from app.core.config import settings
from app.core.database import get_db
from app.core.id_generator import format_doc_id, next_doc_id
from app.core.md_import import (
    parameter_name_collisions,
    parse_markdown_document,
    rename_parameters,
)
from app.core.reqif import (
    FOREIGN_ID_HINTS,
    TEXT_ATTRIBUTE_HINTS,
    TITLE_ATTRIBUTE_HINTS,
    ReqIFObject,
    ReqIFParseError,
)
from app.core.reqif_policy import read_reqif_upload
from app.core.security import get_current_user, require_project_access
from app.core.tc_steps import text_to_rows
from app.core.testrail import (
    TestRailCase,
    TestRailParseError,
    detect_columns,
    parse_testrail_csv,
    parse_testrail_xml,
    read_csv_header,
)
from app.models import (
    ArtefactLink,
    ChangeRequest,
    Defect,
    DesignItem,
    Document,
    Project,
    ProjectVariable,
    Requirement,
    RequirementLink,
    RiskItem,
    TestCase,
    TestConcept,
    TestSuite,
    TestSuiteItem,
)
from app.models.user import User
from app.services.audit import record_audit_event
from app.services.import_attempts import begin_import_attempt, finish_import_attempt
from app.services.notification_service import notify
from app.services.reqif_worker import (
    ReqIFProcessingTimeout,
    parse_in_worker,
    parse_reqif_in_worker,
)

router = APIRouter()


class ImportRequest(BaseModel):
    source_project_id: int
    doc_type: str  # "REQ" or "TC"
    doc_ids: list[int]
    include_links: bool = True


class ImportResult(BaseModel):
    imported: int
    skipped: int
    new_ids: list[str]
    errors: list[str]


class TestCaseImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    new_ids: list[str]
    errors: list[str]


def _extract_numeric_suffix(item_id: str, prefix_len: int) -> int:
    try:
        return int(item_id[prefix_len:])
    except (ValueError, IndexError):
        return 0


def _copied_resource(doc_type: str) -> str:
    """The permission resource of the documents a project-to-project copy moves."""
    return "requirement" if doc_type == "REQ" else "test_case"


@router.post("/projects/{project_id}/import", response_model=ImportResult, status_code=201)
async def import_docs(
    project_id: int,
    data: ImportRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    target_project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not target_project:
        raise HTTPException(status_code=404, detail="Target project not found")

    source_project = (
        await db.execute(select(Project).where(Project.id == data.source_project_id))
    ).scalar_one_or_none()
    if not source_project:
        raise HTTPException(status_code=404, detail="Source project not found")

    if project_id == data.source_project_id:
        raise HTTPException(status_code=400, detail="Cannot import from the same project")

    await require_project_access(
        db, current_user, target_project.id, permission=("import", _copied_resource(data.doc_type))
    )
    await require_project_access(
        db,
        current_user,
        source_project.id,
        permission=("export", _copied_resource(data.doc_type)),
    )

    result = ImportResult(imported=0, skipped=0, new_ids=[], errors=[])
    await record_audit_event(
        db,
        "import.run",
        target_type="project",
        target_id=target_project.id,
        project_id=target_project.id,
        details={"kind": "copy", "doc_type": data.doc_type, "source_project_id": source_project.id},
    )

    if data.doc_type == "REQ":
        await _import_requirements(db, data.doc_ids, source_project, target_project, result)
    elif data.doc_type == "TC":
        await _import_test_cases(db, data.doc_ids, source_project, target_project, result)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported doc_type: {data.doc_type}. Supported: REQ, TC",
        )

    return result


async def _get_next_req_num(db: AsyncSession, project_id: int, prefix: str) -> int:
    search_prefix = f"{prefix}-REQ-"
    rows = (
        (
            await db.execute(
                select(Requirement.req_id).where(
                    Requirement.project_id == project_id,
                    Requirement.req_id.like(f"{search_prefix}%"),
                )
            )
        )
        .scalars()
        .all()
    )
    max_num = 0
    for rid in rows:
        num = _extract_numeric_suffix(rid, len(search_prefix))
        if num > max_num:
            max_num = num
    return max_num + 1


async def _get_next_tc_num(db: AsyncSession, project_id: int, prefix: str) -> int:
    search_prefix = f"{prefix}-TC-"
    rows = (
        (
            await db.execute(
                select(TestCase.tc_id).where(
                    TestCase.project_id == project_id,
                    TestCase.tc_id.like(f"{search_prefix}%"),
                )
            )
        )
        .scalars()
        .all()
    )
    max_num = 0
    for rid in rows:
        num = _extract_numeric_suffix(rid, len(search_prefix))
        if num > max_num:
            max_num = num
    return max_num + 1


async def _import_requirements(
    db: AsyncSession,
    doc_ids: list[int],
    source_project: Project,
    target_project: Project,
    result: ImportResult,
):
    next_num = await _get_next_req_num(db, target_project.id, target_project.prefix)

    # Load the whole selection up front: an import of several hundred rows was otherwise
    # a statement per row.
    sources_by_id = (
        {
            row.id: row
            for row in (
                (
                    await db.execute(
                        select(Requirement).where(
                            Requirement.id.in_(doc_ids),
                            Requirement.project_id == source_project.id,
                        )
                    )
                )
                .scalars()
                .all()
            )
        }
        if doc_ids
        else {}
    )

    for src_id in doc_ids:
        src = sources_by_id.get(src_id)
        if not src:
            result.errors.append(f"Requirement {src_id} not found in source project")
            result.skipped += 1
            continue

        new_req_id = format_doc_id(target_project.prefix, "REQ", next_num)
        imported = Requirement(
            project_id=target_project.id,
            req_id=new_req_id,
            title=src.title,
            description=src.description,
            content_json=src.content_json,
            content_html=src.content_html,
            status="Draft",
            priority=src.priority,
            req_type=src.req_type,
            req_origin=src.req_origin,
            source_ref=src.req_id,
            source_project_id=source_project.id,
        )
        db.add(imported)
        result.new_ids.append(new_req_id)
        result.imported += 1
        next_num += 1

    await db.flush()


async def _import_test_cases(
    db: AsyncSession,
    doc_ids: list[int],
    source_project: Project,
    target_project: Project,
    result: ImportResult,
):
    next_num = await _get_next_tc_num(db, target_project.id, target_project.prefix)

    # Load the whole selection up front: an import of several hundred rows was otherwise
    # a statement per row.
    sources_by_id = (
        {
            row.id: row
            for row in (
                (
                    await db.execute(
                        select(TestCase).where(
                            TestCase.id.in_(doc_ids),
                            TestCase.project_id == source_project.id,
                        )
                    )
                )
                .scalars()
                .all()
            )
        }
        if doc_ids
        else {}
    )

    for src_id in doc_ids:
        src = sources_by_id.get(src_id)
        if not src:
            result.errors.append(f"TestCase {src_id} not found in source project")
            result.skipped += 1
            continue

        new_tc_id = format_doc_id(target_project.prefix, "TC", next_num)
        imported = TestCase(
            project_id=target_project.id,
            tc_id=new_tc_id,
            title=src.title,
            description=src.description,
            content_json=src.content_json,
            content_html=src.content_html,
            preconditions=src.preconditions,
            steps=src.steps,
            status="Draft",
            source_ref=src.tc_id,
            source_project_id=source_project.id,
        )
        db.add(imported)
        result.new_ids.append(new_tc_id)
        result.imported += 1
        next_num += 1

    await db.flush()


# ==================== ReqIF import (DOORS / Polarion / Jama) ====================


class ReqIFImportResult(BaseModel):
    imported: int
    skipped: int
    links_created: int
    specifications: int
    new_ids: list[str]
    errors: list[str]


def _map_link_type(type_name: Optional[str]) -> str:
    if not type_name:
        return "depends_on"
    t = type_name.strip().lower()
    if "refine" in t:
        return "refines"
    if "deriv" in t:
        return "derived_from"
    if "satisf" in t:
        return "satisfies"
    if "depend" in t:
        return "depends_on"
    slug = re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:30]
    return slug or "depends_on"


def _requirement_title(obj: ReqIFObject) -> str:
    title = obj.long_name or obj.first_attr(TITLE_ATTRIBUTE_HINTS)
    if not title:
        body = obj.first_attr(TEXT_ATTRIBUTE_HINTS)
        if body:
            title = body.splitlines()[0]
    title = (title or "Untitled requirement").strip()
    return title[:500]


@router.post(
    "/projects/{project_id}/import/reqif",
    response_model=ReqIFImportResult,
    status_code=201,
)
async def import_reqif(
    project_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Import a ReqIF (``.reqif`` / ``.reqifz``) export as project requirements."""
    target_project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not target_project:
        raise HTTPException(status_code=404, detail="Target project not found")

    await require_project_access(
        db, current_user, target_project.id, permission=("import", "requirement")
    )

    attempt = await begin_import_attempt(db, user_id=current_user.id, project_id=target_project.id)
    await record_audit_event(
        db,
        "import.run",
        target_type="project",
        target_id=target_project.id,
        project_id=target_project.id,
        details={"kind": "reqif"},
    )
    attempt_id = attempt.id
    try:
        raw = await read_reqif_upload(file)
        bundle = await parse_reqif_in_worker(raw)
    except ReqIFProcessingTimeout as exc:
        await finish_import_attempt(db, attempt_id, "timeout")
        raise HTTPException(status_code=504, detail=str(exc))
    except ReqIFParseError as exc:
        await finish_import_attempt(db, attempt_id, "failed")
        status_code = 413 if "25 MiB" in str(exc) and "request" in str(exc) else 422
        raise HTTPException(status_code=status_code, detail=f"Could not parse ReqIF file: {exc}")

    result = ReqIFImportResult(
        imported=0,
        skipped=0,
        links_created=0,
        specifications=len(bundle.specifications),
        new_ids=[],
        errors=[],
    )

    prefix = target_project.prefix
    next_num = await _get_next_req_num(db, target_project.id, prefix)

    # Existing source_refs let a re-import reuse rather than duplicate objects.
    existing_rows = (
        await db.execute(
            select(Requirement.source_ref, Requirement.id).where(
                Requirement.project_id == target_project.id,
                Requirement.source_ref.isnot(None),
            )
        )
    ).all()
    ref_to_req_id: Dict[str, int] = {ref: rid for ref, rid in existing_rows if ref}

    created: List[Requirement] = []

    for object_ref, parent_ref in bundle.ordered_object_refs():
        obj = bundle.objects.get(object_ref)
        if obj is None:
            continue

        source_ref = obj.identifier[:100]
        if source_ref in ref_to_req_id:
            result.skipped += 1
            continue

        parent_id = ref_to_req_id.get(parent_ref[:100]) if parent_ref else None
        new_req_id = format_doc_id(prefix, "REQ", next_num)
        priority = (obj.attributes.get("priority") or "Medium").strip()[:20] or "Medium"

        requirement = Requirement(
            project_id=target_project.id,
            parent_id=parent_id,
            req_id=new_req_id,
            title=_requirement_title(obj),
            description=obj.first_attr(TEXT_ATTRIBUTE_HINTS),
            content_html=obj.first_html(TEXT_ATTRIBUTE_HINTS),
            status="Draft",
            priority=priority,
            req_origin="External",
            source_ref=source_ref,
        )
        db.add(requirement)
        await db.flush()
        ref_to_req_id[source_ref] = requirement.id
        # foreign id (tool's own key), if any, is stored separately for later dedupe
        foreign = obj.first_attr(FOREIGN_ID_HINTS)
        if foreign:
            ref_to_req_id.setdefault(foreign[:100], requirement.id)

        created.append(requirement)
        result.new_ids.append(new_req_id)
        result.imported += 1
        next_num += 1

    # Spec relations -> requirement links (only when both ends exist)
    seen_links: set = set()
    known_ids = set(ref_to_req_id.values())
    if known_ids:
        existing_links = (
            await db.execute(
                select(
                    RequirementLink.source_id,
                    RequirementLink.target_id,
                    RequirementLink.link_type,
                ).where(RequirementLink.source_id.in_(known_ids))
            )
        ).all()
        for s_id, t_id, l_type in existing_links:
            seen_links.add((s_id, t_id, l_type))
    for rel in bundle.relations:
        src_id = ref_to_req_id.get(rel.source_ref[:100])
        tgt_id = ref_to_req_id.get(rel.target_ref[:100])
        if not (src_id and tgt_id) or src_id == tgt_id:
            continue
        link_type = _map_link_type(rel.type_name)
        dedupe = (src_id, tgt_id, link_type)
        if dedupe in seen_links:
            continue
        seen_links.add(dedupe)
        db.add(RequirementLink(source_id=src_id, target_id=tgt_id, link_type=link_type))
        result.links_created += 1

    await db.flush()

    for requirement in created:
        await log_artefact_activity(
            db,
            "requirement",
            requirement.id,
            "created",
            f"{current_user.full_name} imported requirement {requirement.req_id} from ReqIF",
        )

    await finish_import_attempt(db, attempt_id, "completed")
    return result


def _import_rows_from_csv(raw: bytes) -> List[dict]:
    """Parse the exported CSV into per-test-case dicts."""
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    return [{(k or "").strip(): (v or "") for k, v in row.items()} for row in reader]


def _import_rows_from_xml(raw: bytes) -> List[dict]:
    """Parse the exported XML into per-test-case dicts."""
    root = SafeET.fromstring(raw)
    rows = []
    for node in root.findall("test-case"):
        rows.append(
            {
                "tc_id": node.get("id", ""),
                "title": node.findtext("title", ""),
                "status": node.findtext("status", ""),
                "visibility": node.findtext("visibility", ""),
                "preconditions": node.findtext("preconditions", ""),
                "steps": node.findtext("steps", ""),
                "description": node.findtext("description", ""),
            }
        )
    return rows


@router.post(
    "/projects/{project_id}/import/test-cases",
    response_model=TestCaseImportResult,
    status_code=201,
)
async def import_test_cases_file(
    project_id: int,
    format: str = Query("csv", pattern="^(csv|xml)$"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Import test cases from a CSV or XML file in Bloom's export format (round-trip).

    A row whose tc_id already exists updates that test case; a new or absent tc_id
    creates one with a minted id. Returns created/updated/skipped counts.
    """
    target_project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not target_project:
        raise HTTPException(status_code=404, detail="Target project not found")
    await require_project_access(
        db,
        current_user,
        target_project.id,
        permission=("import", "test_case"),
    )

    attempt = await begin_import_attempt(db, user_id=current_user.id, project_id=target_project.id)
    await record_audit_event(
        db,
        "import.run",
        target_type="project",
        target_id=target_project.id,
        project_id=target_project.id,
        details={"kind": "test_cases_file"},
    )
    attempt_id = attempt.id
    raw = await file.read()
    if len(raw) > 5_000_000:
        await finish_import_attempt(db, attempt_id, "failed")
        raise HTTPException(status_code=413, detail="Import file too large")
    try:
        rows = _import_rows_from_csv(raw) if format == "csv" else _import_rows_from_xml(raw)
    except Exception as exc:  # noqa: BLE001 - surface any parse failure as a 400
        await finish_import_attempt(db, attempt_id, "failed")
        raise HTTPException(status_code=400, detail=f"Could not parse {format.upper()}: {exc}")

    created = updated = skipped = 0
    new_ids: List[str] = []
    errors: List[str] = []
    prefix = target_project.prefix
    next_num = await _get_next_tc_num(db, target_project.id, prefix)
    for index, row in enumerate(rows, start=1):
        title = (row.get("title") or "").strip()
        if not title:
            skipped += 1
            errors.append(f"row {index}: missing title")
            continue
        tc_id = (row.get("tc_id") or "").strip()
        steps = text_to_rows(row.get("steps"))
        status = (row.get("status") or "").strip() or "Draft"
        visibility = (row.get("visibility") or "").strip()
        description = (row.get("description") or "").strip() or None
        preconditions = (row.get("preconditions") or "").strip() or None
        existing = None
        if tc_id:
            existing = (
                await db.execute(
                    select(TestCase).where(
                        TestCase.project_id == target_project.id,
                        TestCase.tc_id == tc_id,
                    )
                )
            ).scalar_one_or_none()
        if existing:
            existing.title = title
            existing.description = description
            existing.preconditions = preconditions
            existing.steps = steps
            existing.status = status
            if visibility:
                existing.visibility = visibility
            await db.flush()
            await log_artefact_activity(
                db,
                "test-case",
                existing.id,
                "updated",
                f"{current_user.full_name} updated test case {existing.tc_id} via import",
            )
            updated += 1
        else:
            new_tc_id = format_doc_id(prefix, "TC", next_num)
            next_num += 1
            kwargs = dict(
                project_id=target_project.id,
                tc_id=new_tc_id,
                title=title,
                description=description,
                preconditions=preconditions,
                steps=steps,
                status=status,
            )
            if visibility:
                kwargs["visibility"] = visibility
            test_case = TestCase(**kwargs)
            db.add(test_case)
            await db.flush()
            await log_artefact_activity(
                db,
                "test-case",
                test_case.id,
                "created",
                f"{current_user.full_name} imported test case {test_case.tc_id}",
            )
            created += 1
            new_ids.append(new_tc_id)
    await finish_import_attempt(db, attempt_id, "completed")
    return TestCaseImportResult(
        created=created, updated=updated, skipped=skipped, new_ids=new_ids, errors=errors
    )


# type code -> (model, id attribute, id type code, title attribute, extra kwargs)
ARTEFACT_FACTORY = {
    "REQ": (Requirement, "req_id", "REQ", "title", {}),
    "DES": (DesignItem, "design_id", "DES", "title", {}),
    "RSK": (RiskItem, "risk_id", "RSK", "title", {}),
    "CPT": (TestConcept, "concept_id", "CPT", "name", {}),
    "TC": (TestCase, "tc_id", "TC", "title", {}),
    "DEF": (Defect, "defect_id", "DEF", "title", {}),
    "CHG": (ChangeRequest, "change_id", "CHG", "title", {}),
    "SPEC": (Document, "doc_id", "SPEC", "title", {"doc_type": "SPEC"}),
    "STD": (Document, "doc_id", "STD", "title", {"doc_type": "STD"}),
}

ARTEFACT_SLUG_FOR_CODE = {
    "REQ": "requirements",
    "DES": "designs",
    "RSK": "risks",
    "CPT": "test-concepts",
    "TC": "test-cases",
    "DEF": "defects",
    "CHG": "changes",
    "SPEC": "documents",
    "STD": "documents",
}

# Types for which the uploader is prompted to check link necessity.
LINK_REVIEW_CODES = {"REQ", "DES", "CPT", "SPEC", "STD"}

ARTEFACT_TYPE_FOR_CODE = {
    "REQ": "requirement",
    "DES": "design",
    "RSK": "risk",
    "CPT": "test-concept",
    "TC": "test-case",
    "DEF": "defect",
    "CHG": "change",
    "SPEC": "document",
    "STD": "document",
}


class ClassifiedSection(BaseModel):
    type_code: Optional[str]
    title: str


class MarkdownImportResult(BaseModel):
    doc_type: Optional[str]
    parameters_created: int
    parameter_collisions: List[str]
    parameters_renamed: dict[str, str] = {}
    artefacts_created: int
    artefacts_skipped: int
    notifications_created: int
    sections: List[ClassifiedSection]


def _collision_actions(raw: Optional[str]) -> dict:
    """The uploader's action per colliding parameter name, keyed by the lower-cased name."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("The collision actions are not valid JSON.")
    if not isinstance(data, dict):
        raise ValueError("The collision actions must be an object keyed by parameter name.")
    actions = {}
    for name, choice in data.items():
        action = choice.get("action") if isinstance(choice, dict) else None
        if action == "existing":
            actions[str(name).strip().lower()] = {"action": "existing"}
        elif action == "rename" and str(choice.get("to") or "").strip():
            new = str(choice["to"]).strip()
            if not re.fullmatch(r"[^{}:,\n]+", new):
                raise ValueError(f"The new name {new!r} for {name} is not a valid parameter name.")
            actions[str(name).strip().lower()] = {"action": "rename", "to": new}
        else:
            raise ValueError(f"Choose 'existing' or 'rename' with a new name for {name}.")
    return actions


@router.post(
    "/projects/{project_id}/import/markdown",
    response_model=MarkdownImportResult,
    status_code=201,
)
async def import_markdown(
    project_id: int,
    default_type: Optional[str] = Query(None),
    file: UploadFile = File(...),
    collision_actions: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Import a Markdown document: create its parameters and one artefact per
    classified section.

    A parameter whose name already exists in the project is never overwritten. While
    any such name has no action, nothing is imported and the answer (409) lists each
    one with its existing and imported value. ``collision_actions`` maps a name to
    ``{"action": "existing"}`` (keep the project's value; the text refers to it) or
    ``{"action": "rename", "to": NEW}`` (create NEW with the imported value and refer
    to NEW in the imported text).
    """
    target_project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not target_project:
        raise HTTPException(status_code=404, detail="Target project not found")
    await require_project_access(
        db,
        current_user,
        target_project.id,
        permission=("import", "document"),
    )

    try:
        actions = _collision_actions(collision_actions)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    attempt = await begin_import_attempt(db, user_id=current_user.id, project_id=target_project.id)
    await record_audit_event(
        db,
        "import.run",
        target_type="project",
        target_id=target_project.id,
        project_id=target_project.id,
        details={"kind": "markdown"},
    )
    attempt_id = attempt.id
    raw = await file.read()
    if len(raw) > 5_000_000:
        await finish_import_attempt(db, attempt_id, "failed")
        raise HTTPException(status_code=413, detail="Import file too large")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        await finish_import_attempt(db, attempt_id, "failed")
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text")

    existing = {
        key.strip().lower(): value
        for key, value in (
            await db.execute(
                select(ProjectVariable.key, ProjectVariable.value).where(
                    ProjectVariable.project_id == target_project.id
                )
            )
        ).all()
    }
    parsed = parse_markdown_document(text, default_type=default_type)
    collisions = parameter_name_collisions(parsed.parameters, existing)
    imported_values = {p.name.strip().lower(): p.value for p in parsed.parameters}
    unresolved = [name for name in collisions if name.strip().lower() not in actions]
    if unresolved:
        await finish_import_attempt(db, attempt_id, "failed")
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Parameter names already exist in the project. Choose an action for each.",
                "collisions": [
                    {
                        "name": name,
                        "existing_value": existing.get(name.strip().lower(), ""),
                        "imported_value": imported_values.get(name.strip().lower(), ""),
                    }
                    for name in unresolved
                ],
            },
        )
    renames = {
        name: actions[name.strip().lower()]["to"]
        for name in collisions
        if actions[name.strip().lower()]["action"] == "rename"
    }
    kept = [name for name in collisions if name not in renames]
    if renames:
        taken = set(existing) | {name.strip().lower() for name in imported_values} - {
            old.strip().lower() for old in renames
        }
        for old, new in renames.items():
            if new.strip().lower() in taken:
                await finish_import_attempt(db, attempt_id, "failed")
                raise HTTPException(
                    status_code=422,
                    detail=f"The new name {new!r} for {old} is already taken.",
                )
        parsed = parse_markdown_document(
            rename_parameters(text, renames), default_type=default_type
        )
    blocked = {name.strip().lower() for name in kept} | set(existing)

    created = 0
    done: set = set()
    for parameter in parsed.parameters:
        key_norm = parameter.name.strip().lower()
        if not key_norm or key_norm in blocked or key_norm in done:
            continue
        db.add(
            ProjectVariable(
                project_id=target_project.id,
                kind="variable",
                key=parameter.name.strip(),
                value=parameter.value,
            )
        )
        done.add(key_norm)
        created += 1

    await db.flush()

    artefacts_created = 0
    artefacts_skipped = 0
    notifications_created = 0
    for section in parsed.sections:
        title = section.title.strip()
        if not title:
            continue
        factory = ARTEFACT_FACTORY.get(section.type_code or "")
        if factory is None:
            artefacts_skipped += 1
            continue
        model, id_attr, id_type_code, title_attr, extra = factory
        source_marker = f"md:{section.type_code}:{title}"[:100]
        if hasattr(model, "source_ref"):
            duplicate = (
                await db.execute(
                    select(model.id).where(
                        model.project_id == target_project.id,
                        model.source_ref == source_marker,
                    )
                )
            ).scalar_one_or_none()
            if duplicate is not None:
                artefacts_skipped += 1
                continue
        new_id = await next_doc_id(
            db,
            model,
            getattr(model, id_attr),
            target_project.id,
            target_project.prefix,
            id_type_code,
        )
        kwargs = {"project_id": target_project.id, id_attr: new_id, title_attr: title, **extra}
        instance = model(**kwargs)
        if section.body and hasattr(instance, "description"):
            instance.description = section.body
        if section.steps and hasattr(instance, "steps"):
            instance.steps = section.steps
        if hasattr(instance, "source_ref"):
            instance.source_ref = source_marker
        db.add(instance)
        await db.flush()
        await log_artefact_activity(
            db,
            ARTEFACT_TYPE_FOR_CODE[section.type_code],
            instance.id,
            "created",
            f"{current_user.full_name} imported {new_id} from Markdown",
        )
        artefacts_created += 1
        slug = ARTEFACT_SLUG_FOR_CODE.get(section.type_code, "docs")
        needs_review = section.type_code in LINK_REVIEW_CODES
        await notify(
            db,
            user_id=current_user.id,
            event_type="import_unlinked",
            title=f"Link {new_id}",
            project_id=target_project.id,
            body=(
                f"{new_id} was imported from Markdown and has no links yet. "
                + (
                    "Check the necessity of relevant links in the text and the relationship tree."
                    if needs_review
                    else "Add any relevant links."
                )
            ),
            link_path=f"/projects/{target_project.prefix}/docs/{slug}/{new_id}",
        )
        notifications_created += 1

    await db.flush()
    await finish_import_attempt(db, attempt_id, "completed")
    return MarkdownImportResult(
        doc_type=parsed.doc_type,
        parameters_created=created,
        parameter_collisions=kept,
        parameters_renamed=renames,
        artefacts_created=artefacts_created,
        artefacts_skipped=artefacts_skipped,
        notifications_created=notifications_created,
        sections=[
            ClassifiedSection(type_code=section.type_code, title=section.title)
            for section in parsed.sections
        ],
    )


class TestRailImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    suites_created: list[str]
    links_created: int
    new_ids: list[str]
    errors: list[str]


class TestRailColumns(BaseModel):
    columns: list[str]
    detected: dict[str, str]


def _testrail_body(case: TestRailCase, unmatched: list) -> str:
    """The metadata paragraph a TestRail case leaves in the test case body."""
    facts = [
        (
            f"Imported from TestRail case {case.case_id}."
            if case.case_id
            else "Imported from TestRail."
        )
    ]
    for label, value in (
        ("Type", case.case_type),
        ("Priority", case.priority),
        ("Estimate", case.estimate),
    ):
        if value:
            facts.append(f"{label}: {value}.")
    if unmatched:
        facts.append("References: " + ", ".join(unmatched) + ".")
    return " ".join(facts)


async def _testrail_project(db: AsyncSession, project_id: int, current_user: User) -> Project:
    """The target project, after the test-case import permission check."""
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Target project not found")
    await require_project_access(db, current_user, project.id, permission=("import", "test_case"))
    return project


@router.post("/projects/{project_id}/import/testrail/columns", response_model=TestRailColumns)
async def testrail_csv_columns(
    project_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """The columns of a TestRail CSV export and the fields Bloom recognised in them."""
    await _testrail_project(db, project_id, current_user)
    try:
        raw = await read_reqif_upload(file)
        header = read_csv_header(raw)
    except ReqIFParseError:
        raise HTTPException(status_code=413, detail="The file exceeds the 25 MiB import limit.")
    except TestRailParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return TestRailColumns(columns=header, detected=detect_columns(header))


@router.post(
    "/projects/{project_id}/import/testrail",
    response_model=TestRailImportResult,
    status_code=201,
)
async def import_testrail(
    project_id: int,
    format: str = Query("xml", pattern="^(xml|csv)$"),
    file: UploadFile = File(...),
    mapping: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Import a TestRail XML or CSV export as test cases, suites and requirement links.

    A case carries ``source_ref = testrail:C123``, so importing the same export again
    updates the cases instead of duplicating them.
    """
    project = await _testrail_project(db, project_id, current_user)
    column_mapping = None
    if mapping:
        try:
            column_mapping = json.loads(mapping)
        except ValueError:
            raise HTTPException(status_code=422, detail="The column mapping is not valid JSON.")
        if not isinstance(column_mapping, dict):
            raise HTTPException(status_code=422, detail="The column mapping must be an object.")

    attempt = await begin_import_attempt(db, user_id=current_user.id, project_id=project.id)
    await record_audit_event(
        db,
        "import.run",
        target_type="project",
        target_id=project.id,
        project_id=project.id,
        details={"kind": "testrail"},
    )
    attempt_id = attempt.id
    parser = (
        parse_testrail_xml
        if format == "xml"
        else functools.partial(parse_testrail_csv, mapping=column_mapping)
    )
    try:
        raw = await read_reqif_upload(file)
        cases = await parse_in_worker(parser, raw, error_cls=TestRailParseError, label="TestRail")
    except ReqIFParseError:
        await finish_import_attempt(db, attempt_id, "failed")
        raise HTTPException(status_code=413, detail="The file exceeds the 25 MiB import limit.")
    except ReqIFProcessingTimeout as exc:
        await finish_import_attempt(db, attempt_id, "timeout")
        raise HTTPException(status_code=504, detail=str(exc))
    except TestRailParseError as exc:
        await finish_import_attempt(db, attempt_id, "failed")
        raise HTTPException(status_code=422, detail=f"Could not read the TestRail file: {exc}")

    requirements = {
        req_id.upper(): req_pk
        for req_pk, req_id in (
            await db.execute(
                select(Requirement.id, Requirement.req_id).where(
                    Requirement.project_id == project.id
                )
            )
        ).all()
    }
    suites = {
        suite.name: suite
        for suite in (await db.execute(select(TestSuite).where(TestSuite.project_id == project.id)))
        .scalars()
        .all()
    }
    result = TestRailImportResult(
        created=0, updated=0, skipped=0, suites_created=[], links_created=0, new_ids=[], errors=[]
    )
    prefix = project.prefix
    next_num = await _get_next_tc_num(db, project.id, prefix)

    for index, case in enumerate(cases, start=1):
        if not case.title:
            result.skipped += 1
            result.errors.append(f"case {case.case_id or index}: missing title")
            continue
        matched = [requirements[t.upper()] for t in case.references if t.upper() in requirements]
        unmatched = [t for t in case.references if t.upper() not in requirements]
        description = _testrail_body(case, unmatched)
        source_ref = f"testrail:{case.case_id}"[:100] if case.case_id else None
        test_case = None
        if source_ref:
            test_case = (
                await db.execute(
                    select(TestCase).where(
                        TestCase.project_id == project.id, TestCase.source_ref == source_ref
                    )
                )
            ).scalar_one_or_none()
        if test_case is not None:
            test_case.title = case.title
            test_case.description = description
            test_case.preconditions = case.preconditions or None
            test_case.steps = case.rows or None
            await db.flush()
            await log_artefact_activity(
                db,
                "test-case",
                test_case.id,
                "updated",
                f"{current_user.full_name} updated {test_case.tc_id} from TestRail {case.case_id}",
            )
            result.updated += 1
        else:
            tc_id = format_doc_id(prefix, "TC", next_num)
            next_num += 1
            test_case = TestCase(
                project_id=project.id,
                tc_id=tc_id,
                title=case.title,
                description=description,
                preconditions=case.preconditions or None,
                steps=case.rows or None,
                status="Draft",
                source_ref=source_ref,
            )
            db.add(test_case)
            await db.flush()
            await log_artefact_activity(
                db,
                "test-case",
                test_case.id,
                "created",
                f"{current_user.full_name} imported {tc_id} from TestRail",
            )
            result.created += 1
            result.new_ids.append(tc_id)

        for requirement_pk in matched:
            linked = (
                await db.execute(
                    select(ArtefactLink.id).where(
                        ArtefactLink.project_id == project.id,
                        ArtefactLink.source_type == "TC",
                        ArtefactLink.source_id == test_case.id,
                        ArtefactLink.target_type == "REQ",
                        ArtefactLink.target_id == requirement_pk,
                        ArtefactLink.role == "verifies",
                    )
                )
            ).scalar_one_or_none()
            if linked is None:
                db.add(
                    ArtefactLink(
                        project_id=project.id,
                        source_type="TC",
                        source_id=test_case.id,
                        target_type="REQ",
                        target_id=requirement_pk,
                        role="verifies",
                    )
                )
                result.links_created += 1

        if case.sections and case.sections[0]:
            name = case.sections[0][:255]
            suite = suites.get(name)
            if suite is None:
                suite = TestSuite(
                    project_id=project.id,
                    suite_id=await next_doc_id(
                        db, TestSuite, TestSuite.suite_id, project.id, prefix, "TS"
                    ),
                    name=name,
                )
                db.add(suite)
                await db.flush()
                suites[name] = suite
                result.suites_created.append(suite.suite_id)
            in_suite = (
                await db.execute(
                    select(TestSuiteItem.id).where(
                        TestSuiteItem.suite_id == suite.id,
                        TestSuiteItem.test_case_id == test_case.id,
                    )
                )
            ).scalar_one_or_none()
            if in_suite is None:
                order = len(
                    (
                        await db.execute(
                            select(TestSuiteItem.id).where(TestSuiteItem.suite_id == suite.id)
                        )
                    ).all()
                )
                db.add(TestSuiteItem(suite_id=suite.id, test_case_id=test_case.id, order=order))
        await db.flush()

    await finish_import_attempt(db, attempt_id, "completed")
    return result
