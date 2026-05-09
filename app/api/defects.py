"""Defect API endpoints."""

import logging
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import log_artefact_activity
from app.core.database import get_db
from app.core.external_issue import validate_external_fields
from app.core.id_generator import normalize_doc_id
from app.core.security import get_current_user, require_role
from app.models import Defect, IntegrationSetting, Project
from app.models.user import User, UserRole
from app.schemas import DefectCreate, DefectResponse, DefectUpdate

logger = logging.getLogger(__name__)

router = APIRouter()

TERMINAL_STATUSES = frozenset({"Closed", "Rejected", "Duplicate"})


def _defect_response(item: Defect) -> DefectResponse:
    return DefectResponse.model_validate(item)


@router.get("", response_model=list[DefectResponse])
async def list_defects(
    project_id: int = Query(..., description="Filter by project ID"),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    query = select(Defect).where(Defect.project_id == project_id)
    if status:
        query = query.where(Defect.status == status)
    if severity:
        query = query.where(Defect.severity == severity)
    query = query.order_by(Defect.created_at.desc())
    result = await db.execute(query)
    return [_defect_response(item) for item in result.scalars().all()]


@router.post("", response_model=DefectResponse, status_code=201)
async def create_defect(
    data: DefectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    project = (
        await db.execute(select(Project).where(Project.id == data.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        defect_id = normalize_doc_id(
            data.defect_id,
            expected_type_code="DEF",
            expected_project_prefix=project.prefix,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = await db.execute(
        select(Defect).where(
            Defect.project_id == data.project_id,
            Defect.defect_id == defect_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Defect with this ID already exists")

    ext_error = validate_external_fields(
        data.external_tracker,
        data.external_issue_url,
        data.external_repo_full_name,
        data.external_issue_number,
    )
    if ext_error:
        raise HTTPException(status_code=422, detail=ext_error)

    item = Defect(
        project_id=data.project_id,
        defect_id=defect_id,
        title=data.title,
        description=data.description,
        status=data.status,
        severity=data.severity,
        priority=data.priority,
        source_type=data.source_type,
        source_id=data.source_id,
        owner_id=data.owner_id,
        reporter_id=data.reporter_id,
        reviewer_id=data.reviewer_id,
        resolution_summary=data.resolution_summary,
        external_tracker=data.external_tracker,
        external_repo_full_name=data.external_repo_full_name,
        external_issue_number=data.external_issue_number,
        external_issue_url=data.external_issue_url,
        external_issue_state=data.external_issue_state,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await log_artefact_activity(
        db,
        "defect",
        item.id,
        "created",
        f"{current_user.full_name} created defect {item.defect_id}",
    )
    return _defect_response(item)


@router.get("/{defect_pk}", response_model=DefectResponse)
async def get_defect(
    defect_pk: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    item = (await db.execute(select(Defect).where(Defect.id == defect_pk))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Defect not found")
    return _defect_response(item)


@router.patch("/{defect_pk}", response_model=DefectResponse)
async def update_defect(
    defect_pk: int,
    data: DefectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (await db.execute(select(Defect).where(Defect.id == defect_pk))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Defect not found")

    updates = data.model_dump(exclude_unset=True)

    merged_tracker = updates.get("external_tracker", item.external_tracker)
    merged_url = updates.get("external_issue_url", item.external_issue_url)
    merged_repo = updates.get("external_repo_full_name", item.external_repo_full_name)
    merged_number = updates.get("external_issue_number", item.external_issue_number)
    ext_error = validate_external_fields(merged_tracker, merged_url, merged_repo, merged_number)
    if ext_error:
        raise HTTPException(status_code=422, detail=ext_error)

    new_status = updates.get("status")

    for field, value in updates.items():
        setattr(item, field, value)

    if new_status and new_status in TERMINAL_STATUSES and item.closed_at is None:
        item.closed_at = datetime.utcnow()
    elif new_status and new_status not in TERMINAL_STATUSES:
        item.closed_at = None

    await db.flush()
    await db.refresh(item)
    await log_artefact_activity(
        db,
        "defect",
        item.id,
        "updated",
        f"{current_user.full_name} updated defect {item.defect_id}",
    )

    syncable_fields = {"title", "status", "description"}
    changed_sync_fields = {k: v for k, v in updates.items() if k in syncable_fields}
    if changed_sync_fields and item.external_tracker:
        from app.api.integrations import sync_defect_to_tracker

        await sync_defect_to_tracker(db, item, changed_sync_fields)

    return _defect_response(item)


@router.delete("/{defect_pk}", status_code=204)
async def delete_defect(
    defect_pk: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (await db.execute(select(Defect).where(Defect.id == defect_pk))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Defect not found")
    await log_artefact_activity(
        db,
        "defect",
        item.id,
        "deleted",
        f"{current_user.full_name} deleted defect {item.defect_id}",
    )
    await db.delete(item)


# ==================== External issue refresh ====================


class RefreshTokenPayload(BaseModel):
    token: str | None = None


@router.post("/{defect_pk}/refresh-external", response_model=DefectResponse)
async def refresh_external_issue(
    defect_pk: int,
    payload: RefreshTokenPayload | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """Fetch current state from GitHub/GitLab and update cached fields.

    If a token is not supplied in the request body, fall back to the project's
    `IntegrationSetting` for the relevant tracker so admins do not have to
    paste a token every refresh.
    """
    item = (await db.execute(select(Defect).where(Defect.id == defect_pk))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Defect not found")
    if (
        not item.external_tracker
        or not item.external_repo_full_name
        or not item.external_issue_number
    ):
        raise HTTPException(status_code=422, detail="Defect has no external issue reference")

    token = payload.token if payload else None
    if not token:
        setting = (
            await db.execute(
                select(IntegrationSetting).where(
                    IntegrationSetting.project_id == item.project_id,
                    IntegrationSetting.tracker == item.external_tracker,
                )
            )
        ).scalar_one_or_none()
        if not setting or not setting.token_encrypted:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"No token configured for {item.external_tracker} on this project. "
                    "Add an integration token in project parameters or pass one explicitly."
                ),
            )
        token = setting.token_encrypted

    try:
        if item.external_tracker == "github":
            result = await _fetch_github_issue(
                item.external_repo_full_name, item.external_issue_number, token
            )
        elif item.external_tracker == "gitlab":
            result = await _fetch_gitlab_issue(
                item.external_repo_full_name, item.external_issue_number, token
            )
        else:
            raise HTTPException(
                status_code=422, detail=f"Unsupported tracker: {item.external_tracker}"
            )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Tracker API returned {exc.response.status_code}",
        ) from exc

    item.external_issue_state = result["state"]
    item.external_last_event_at = datetime.utcnow()

    await db.flush()
    await db.refresh(item)
    await log_artefact_activity(
        db,
        "defect",
        item.id,
        "external_refreshed",
        f"{current_user.full_name} refreshed external issue state to '{result['state']}'",
    )
    return _defect_response(item)


async def _fetch_github_issue(repo: str, number: int, token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo}/issues/{number}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return {"state": data.get("state", "unknown")}


async def _fetch_gitlab_issue(namespace: str, iid: int, token: str) -> dict:
    from urllib.parse import quote

    encoded = quote(namespace, safe="")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://gitlab.com/api/v4/projects/{encoded}/issues/{iid}",
            headers={"PRIVATE-TOKEN": token},
        )
        resp.raise_for_status()
        data = resp.json()
        return {"state": data.get("state", "unknown")}
