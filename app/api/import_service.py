"""
Cross-project import service for docs (REQ/TC).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_project_access, require_role
from app.models import Project, Requirement, TestCase
from app.models.user import User, UserRole

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

    for src_id in doc_ids:
        src = (
            await db.execute(
                select(Requirement).where(
                    Requirement.id == src_id,
                    Requirement.project_id == source_project.id,
                )
            )
        ).scalar_one_or_none()
        if not src:
            result.errors.append(f"Requirement {src_id} not found in source project")
            result.skipped += 1
            continue

        new_req_id = f"{target_project.prefix}-REQ-{next_num:03d}"
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

    for src_id in doc_ids:
        src = (
            await db.execute(
                select(TestCase).where(
                    TestCase.id == src_id, TestCase.project_id == source_project.id
                )
            )
        ).scalar_one_or_none()
        if not src:
            result.errors.append(f"TestCase {src_id} not found in source project")
            result.skipped += 1
            continue

        new_tc_id = f"{target_project.prefix}-TC-{next_num:03d}"
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
