"""External tracker integration endpoints: settings, webhooks, and outbound sync."""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_project_access, require_role
from app.models import (
    Defect,
    DefectSyncEvent,
    IntegrationSetting,
    Project,
    WebhookDelivery,
)
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

# ==================== Integration settings ====================


class IntegrationSettingCreate(BaseModel):
    project_id: int
    tracker: str = Field(..., pattern="^(github|gitlab)$")
    base_url: Optional[str] = None
    token: Optional[str] = None
    webhook_secret: Optional[str] = None
    enabled: bool = True


class IntegrationSettingResponse(BaseModel):
    id: int
    project_id: int
    tracker: str
    base_url: Optional[str] = None
    has_token: bool
    has_webhook_secret: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationSettingUpdate(BaseModel):
    base_url: Optional[str] = None
    token: Optional[str] = None
    webhook_secret: Optional[str] = None
    enabled: Optional[bool] = None


class SyncEventResponse(BaseModel):
    id: int
    defect_id: int
    direction: str
    tracker: str
    event_type: str
    payload_summary: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


def _setting_response(s: IntegrationSetting) -> IntegrationSettingResponse:
    return IntegrationSettingResponse(
        id=s.id,
        project_id=s.project_id,
        tracker=s.tracker,
        base_url=s.base_url,
        has_token=bool(s.token_encrypted),
        has_webhook_secret=bool(s.webhook_secret),
        enabled=s.enabled,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("/settings", response_model=list[IntegrationSettingResponse])
async def list_integration_settings(
    project_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_project_access(db, current_user, project_id)

    rows = (
        (
            await db.execute(
                select(IntegrationSetting)
                .where(IntegrationSetting.project_id == project_id)
                .order_by(IntegrationSetting.tracker)
            )
        )
        .scalars()
        .all()
    )
    return [_setting_response(s) for s in rows]


@router.post("/settings", response_model=IntegrationSettingResponse, status_code=201)
async def create_integration_setting(
    data: IntegrationSettingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    project = (
        await db.execute(select(Project).where(Project.id == data.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await require_project_access(
        db,
        current_user,
        data.project_id,
        roles={UserRole.admin.value},
    )

    existing = (
        await db.execute(
            select(IntegrationSetting).where(
                IntegrationSetting.project_id == data.project_id,
                IntegrationSetting.tracker == data.tracker,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Integration for {data.tracker} already exists in this project",
        )

    setting = IntegrationSetting(
        project_id=data.project_id,
        tracker=data.tracker,
        base_url=data.base_url,
        token_encrypted=data.token,
        webhook_secret=data.webhook_secret,
        enabled=data.enabled,
    )
    db.add(setting)
    await db.flush()
    await db.refresh(setting)
    return _setting_response(setting)


@router.patch("/settings/{setting_id}", response_model=IntegrationSettingResponse)
async def update_integration_setting(
    setting_id: int,
    data: IntegrationSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    setting = (
        await db.execute(select(IntegrationSetting).where(IntegrationSetting.id == setting_id))
    ).scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Integration setting not found")

    await require_project_access(
        db,
        current_user,
        setting.project_id,
        roles={UserRole.admin.value},
    )

    if data.base_url is not None:
        setting.base_url = data.base_url
    if data.token is not None:
        setting.token_encrypted = data.token
    if data.webhook_secret is not None:
        setting.webhook_secret = data.webhook_secret
    if data.enabled is not None:
        setting.enabled = data.enabled

    await db.flush()
    await db.refresh(setting)
    return _setting_response(setting)


@router.delete("/settings/{setting_id}", status_code=204)
async def delete_integration_setting(
    setting_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    setting = (
        await db.execute(select(IntegrationSetting).where(IntegrationSetting.id == setting_id))
    ).scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Integration setting not found")
    await require_project_access(
        db,
        current_user,
        setting.project_id,
        roles={UserRole.admin.value},
    )
    await db.delete(setting)


# ==================== Sync log ====================


@router.get("/sync-events", response_model=list[SyncEventResponse])
async def list_sync_events(
    defect_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    defect = (await db.execute(select(Defect).where(Defect.id == defect_id))).scalar_one_or_none()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    await require_project_access(db, current_user, defect.project_id)

    rows = (
        (
            await db.execute(
                select(DefectSyncEvent)
                .where(DefectSyncEvent.defect_id == defect_id)
                .order_by(DefectSyncEvent.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return [SyncEventResponse.model_validate(e) for e in rows]


# ==================== GitHub webhook ====================

GITHUB_STATUS_MAP = {"open": "Open", "closed": "Closed"}
MAX_WEBHOOK_BODY_BYTES = 1024 * 1024
MAX_WEBHOOKS_PER_15_MINUTES = 60


async def _read_webhook_body(request: Request) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_WEBHOOK_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Webhook body exceeds the 1 MiB limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def _json_payload(body: bytes) -> dict:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook JSON.")
    return payload


async def _reserve_webhook_delivery(
    db: AsyncSession,
    setting: IntegrationSetting,
    tracker: str,
    delivery_id: str,
) -> bool:
    if len(delivery_id) > 255:
        raise HTTPException(status_code=400, detail="Invalid webhook delivery id.")
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        lock_key = int.from_bytes(
            hashlib.sha256(f"webhook:{setting.id}".encode()).digest()[:8],
            "big",
            signed=True,
        )
        await db.execute(select(func.pg_advisory_xact_lock(lock_key)))
    window = datetime.utcnow() - timedelta(minutes=15)
    count = await db.scalar(
        select(func.count(WebhookDelivery.id)).where(
            WebhookDelivery.integration_setting_id == setting.id,
            WebhookDelivery.received_at >= window,
        )
    )
    if (count or 0) >= MAX_WEBHOOKS_PER_15_MINUTES:
        raise HTTPException(
            status_code=429,
            detail="Webhook rate limit exceeded.",
            headers={"Retry-After": "900"},
        )
    existing = await db.scalar(
        select(WebhookDelivery.id).where(
            WebhookDelivery.tracker == tracker,
            WebhookDelivery.delivery_id == delivery_id,
        )
    )
    if existing is not None:
        return False
    db.add(
        WebhookDelivery(
            integration_setting_id=setting.id,
            tracker=tracker,
            delivery_id=delivery_id,
            received_at=datetime.utcnow(),
        )
    )
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return False
    return True


def _verify_github_signature(body: bytes, secret: str, signature: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github/webhook", status_code=200)
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None),
):
    body = await _read_webhook_body(request)
    payload = _json_payload(body)

    if x_github_event != "issues":
        return {"status": "ignored", "reason": "not an issues event"}

    action = payload.get("action", "")
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name", "")
    issue_number = issue.get("number")
    issue_state = issue.get("state", "")

    if not repo_full_name or not issue_number:
        return {"status": "ignored", "reason": "missing repo or issue number"}

    defect = (
        await db.execute(
            select(Defect).where(
                Defect.external_tracker == "github",
                Defect.external_repo_full_name == repo_full_name,
                Defect.external_issue_number == issue_number,
            )
        )
    ).scalar_one_or_none()

    if not defect:
        raise HTTPException(status_code=404, detail="No matching webhook target.")

    # When a webhook secret is configured, a valid signature is REQUIRED —
    # a missing header must reject, otherwise omitting it bypasses auth.
    setting = (
        await db.execute(
            select(IntegrationSetting).where(
                IntegrationSetting.project_id == defect.project_id,
                IntegrationSetting.tracker == "github",
            )
        )
    ).scalar_one_or_none()
    if not setting or not setting.enabled or not setting.webhook_secret:
        raise HTTPException(status_code=403, detail="Webhook is not securely configured.")
    if not x_hub_signature_256 or not _verify_github_signature(
        body, setting.webhook_secret, x_hub_signature_256
    ):
        _log_sync_event(
            db,
            defect.id,
            "inbound",
            "github",
            "signature_failed",
            success=False,
            error="Missing or invalid HMAC signature",
        )
        await db.flush()
        raise HTTPException(status_code=403, detail="Invalid signature")
    if not x_github_delivery:
        raise HTTPException(status_code=400, detail="Missing GitHub delivery id.")
    if not await _reserve_webhook_delivery(db, setting, "github", x_github_delivery):
        return {"status": "duplicate", "delivery": x_github_delivery}

    old_state = defect.external_issue_state
    defect.external_issue_state = issue_state
    defect.external_last_event_at = datetime.utcnow()

    bloom_status = GITHUB_STATUS_MAP.get(issue_state)
    if bloom_status and defect.status != bloom_status:
        defect.status = bloom_status
        if bloom_status == "Closed" and not defect.closed_at:
            defect.closed_at = datetime.utcnow()
        elif bloom_status != "Closed":
            defect.closed_at = None

    _log_sync_event(
        db,
        defect.id,
        "inbound",
        "github",
        f"issues.{action}",
        payload_summary=f"state: {old_state} -> {issue_state}",
        external_event_id=x_github_delivery,
    )

    await db.flush()
    return {"status": "processed", "defect_id": defect.id}


# ==================== GitLab webhook ====================

GITLAB_STATUS_MAP = {"opened": "Open", "closed": "Closed"}


def _verify_gitlab_token(secret: str, header_token: str) -> bool:
    return hmac.compare_digest(secret, header_token)


@router.post("/gitlab/webhook", status_code=200)
async def gitlab_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_gitlab_token: Optional[str] = Header(None),
    x_gitlab_event: Optional[str] = Header(None),
    x_gitlab_event_uuid: Optional[str] = Header(None),
):
    body = await _read_webhook_body(request)
    payload = _json_payload(body)

    if x_gitlab_event != "Issue Hook":
        return {"status": "ignored", "reason": "not an Issue Hook event"}

    attrs = payload.get("object_attributes", {})
    project_info = payload.get("project", {})
    namespace = project_info.get("path_with_namespace", "")
    iid = attrs.get("iid")
    issue_state = attrs.get("state", "")
    action = attrs.get("action", "")

    if not namespace or not iid:
        return {"status": "ignored", "reason": "missing namespace or IID"}

    defect = (
        await db.execute(
            select(Defect).where(
                Defect.external_tracker == "gitlab",
                Defect.external_repo_full_name == namespace,
                Defect.external_issue_number == iid,
            )
        )
    ).scalar_one_or_none()

    if not defect:
        raise HTTPException(status_code=404, detail="No matching webhook target.")

    # When a webhook secret is configured, a valid token is REQUIRED —
    # a missing header must reject, otherwise omitting it bypasses auth.
    setting = (
        await db.execute(
            select(IntegrationSetting).where(
                IntegrationSetting.project_id == defect.project_id,
                IntegrationSetting.tracker == "gitlab",
            )
        )
    ).scalar_one_or_none()
    if not setting or not setting.enabled or not setting.webhook_secret:
        raise HTTPException(status_code=403, detail="Webhook is not securely configured.")
    if not x_gitlab_token or not _verify_gitlab_token(setting.webhook_secret, x_gitlab_token):
        _log_sync_event(
            db,
            defect.id,
            "inbound",
            "gitlab",
            "token_failed",
            success=False,
            error="Missing or invalid GitLab token",
        )
        await db.flush()
        raise HTTPException(status_code=403, detail="Invalid token")
    if not x_gitlab_event_uuid:
        raise HTTPException(status_code=400, detail="Missing GitLab event UUID.")
    if not await _reserve_webhook_delivery(db, setting, "gitlab", x_gitlab_event_uuid):
        return {"status": "duplicate", "uuid": x_gitlab_event_uuid}

    old_state = defect.external_issue_state
    defect.external_issue_state = issue_state
    defect.external_last_event_at = datetime.utcnow()

    bloom_status = GITLAB_STATUS_MAP.get(issue_state)
    if bloom_status and defect.status != bloom_status:
        defect.status = bloom_status
        if bloom_status == "Closed" and not defect.closed_at:
            defect.closed_at = datetime.utcnow()
        elif bloom_status != "Closed":
            defect.closed_at = None

    _log_sync_event(
        db,
        defect.id,
        "inbound",
        "gitlab",
        f"issue.{action}",
        payload_summary=f"state: {old_state} -> {issue_state}",
        external_event_id=x_gitlab_event_uuid,
    )

    await db.flush()
    return {"status": "processed", "defect_id": defect.id}


# ==================== Outbound sync ====================


async def sync_defect_to_tracker(
    db: AsyncSession,
    defect: Defect,
    changed_fields: dict,
) -> None:
    """Push defect changes to the linked external tracker if configured."""
    if not defect.external_tracker or not defect.external_repo_full_name:
        return

    setting = (
        await db.execute(
            select(IntegrationSetting).where(
                IntegrationSetting.project_id == defect.project_id,
                IntegrationSetting.tracker == defect.external_tracker,
                IntegrationSetting.enabled == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()

    if not setting or not setting.token_encrypted:
        return

    try:
        if defect.external_tracker == "github":
            await _push_to_github(defect, setting, changed_fields)
        elif defect.external_tracker == "gitlab":
            await _push_to_gitlab(defect, setting, changed_fields)

        _log_sync_event(
            db,
            defect.id,
            "outbound",
            defect.external_tracker,
            "update_pushed",
            payload_summary=f"fields: {', '.join(changed_fields.keys())}",
        )
        defect.external_last_event_at = datetime.utcnow()
    except Exception as exc:
        logger.warning("Outbound sync failed for defect %s: %s", defect.id, exc)
        _log_sync_event(
            db,
            defect.id,
            "outbound",
            defect.external_tracker,
            "update_failed",
            success=False,
            error=str(exc),
        )


BLOOM_TO_GITHUB_STATE = {"Closed": "closed", "Rejected": "closed"}
BLOOM_TO_GITLAB_STATE = {"Closed": "close", "Rejected": "close"}


async def _push_to_github(
    defect: Defect, setting: IntegrationSetting, changed_fields: dict
) -> None:
    body: dict = {}
    if "title" in changed_fields:
        body["title"] = defect.title
    if "status" in changed_fields:
        gh_state = BLOOM_TO_GITHUB_STATE.get(defect.status)
        if gh_state:
            body["state"] = gh_state
        elif defect.status in ("Open", "Triaged", "In Progress", "Resolved", "Verified"):
            body["state"] = "open"

    if not body:
        return

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(
            f"https://api.github.com/repos/{defect.external_repo_full_name}/issues/{defect.external_issue_number}",
            json=body,
            headers={
                "Authorization": f"Bearer {setting.token_encrypted}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()


async def _push_to_gitlab(
    defect: Defect, setting: IntegrationSetting, changed_fields: dict
) -> None:
    from urllib.parse import quote

    body: dict = {}
    if "title" in changed_fields:
        body["title"] = defect.title
    if "status" in changed_fields:
        gl_event = BLOOM_TO_GITLAB_STATE.get(defect.status)
        if gl_event:
            body["state_event"] = gl_event
        elif defect.status in ("Open", "Triaged", "In Progress", "Resolved", "Verified"):
            body["state_event"] = "reopen"

    if not body:
        return

    base_url = (setting.base_url or "https://gitlab.com").rstrip("/")
    encoded = quote(defect.external_repo_full_name or "", safe="")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{base_url}/api/v4/projects/{encoded}/issues/{defect.external_issue_number}",
            json=body,
            headers={"PRIVATE-TOKEN": setting.token_encrypted or ""},
        )
        resp.raise_for_status()


# ==================== Helpers ====================


def _log_sync_event(
    db: AsyncSession,
    defect_id: int,
    direction: str,
    tracker: str,
    event_type: str,
    payload_summary: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None,
    external_event_id: Optional[str] = None,
) -> None:
    db.add(
        DefectSyncEvent(
            defect_id=defect_id,
            direction=direction,
            tracker=tracker,
            event_type=event_type,
            payload_summary=payload_summary,
            success=success,
            error_message=error,
            external_event_id=external_event_id,
        )
    )
