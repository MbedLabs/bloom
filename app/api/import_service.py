"""
Cross-project import service for docs (REQ/TC).
"""

import csv
import io
import re
from typing import Dict, List, Optional

from defusedxml import ElementTree as SafeET
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import log_artefact_activity
from app.core.database import get_db
from app.core.id_generator import format_doc_id
from app.core.reqif import (
    FOREIGN_ID_HINTS,
    TEXT_ATTRIBUTE_HINTS,
    TITLE_ATTRIBUTE_HINTS,
    ReqIFObject,
    ReqIFParseError,
)
from app.core.reqif_policy import read_reqif_upload
from app.core.security import require_project_access, require_role
from app.models import Project, Requirement, RequirementLink, TestCase
from app.models.user import User, UserRole
from app.services.import_attempts import begin_import_attempt, finish_import_attempt
from app.services.reqif_worker import ReqIFProcessingTimeout, parse_reqif_in_worker

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


@router.post("/projects/{project_id}/import", response_model=ImportResult, status_code=201)
async def import_docs(
    project_id: int,
    data: ImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
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
        db, current_user, target_project.id, roles={UserRole.admin.value, UserRole.maintainer.value}
    )
    await require_project_access(
        db,
        current_user,
        source_project.id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    result = ImportResult(imported=0, skipped=0, new_ids=[], errors=[])

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """Import a ReqIF (``.reqif`` / ``.reqifz``) export as project requirements."""
    target_project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not target_project:
        raise HTTPException(status_code=404, detail="Target project not found")

    await require_project_access(
        db, current_user, target_project.id, roles={UserRole.admin.value, UserRole.maintainer.value}
    )

    attempt = await begin_import_attempt(db, user_id=current_user.id, project_id=target_project.id)
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


def _parse_steps_text(text):
    """Reverse the exported steps text back into a steps JSON list."""
    if not text or not text.strip():
        return None
    steps = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        body = line
        dot = body.find(". ")
        if dot != -1 and body[:dot].isdigit():
            body = body[dot + 2 :]
        if " => " in body:
            action, expected = body.split(" => ", 1)
            steps.append({"action": action.strip(), "expected": expected.strip()})
        else:
            steps.append({"action": body.strip()})
    return steps or None


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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
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
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    attempt = await begin_import_attempt(db, user_id=current_user.id, project_id=target_project.id)
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
        steps = _parse_steps_text(row.get("steps"))
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
