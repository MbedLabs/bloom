"""External tracker integration endpoints: settings, webhooks, and outbound sync."""

import base64
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
    ChangeRequest,
    ChangeRequestSyncEvent,
    Defect,
    DefectSyncEvent,
    IntegrationSetting,
    Project,
    WebhookDelivery,
)
from app.models.user import User, UserRole
from app.services.integration_secrets import (
    decrypt_integration_secret,
    encrypt_integration_secret,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ==================== Integration settings ====================


class IntegrationSettingCreate(BaseModel):
    project_id: int
    tracker: str = Field(..., pattern="^(github|gitlab|jira)$")
    base_url: Optional[str] = None
    # Jira Cloud only: the account owning the API token (Basic auth is
    # `email:api_token`). Ignored by GitHub and GitLab.
    account_email: Optional[str] = None
    token: Optional[str] = None
    webhook_secret: Optional[str] = None
    enabled: bool = True


class IntegrationSettingResponse(BaseModel):
    id: int
    project_id: int
    tracker: str
    base_url: Optional[str] = None
    account_email: Optional[str] = None
    has_token: bool
    has_webhook_secret: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationSettingUpdate(BaseModel):
    base_url: Optional[str] = None
    account_email: Optional[str] = None
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
        account_email=s.account_email,
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
        account_email=data.account_email,
        token_encrypted=(encrypt_integration_secret(data.token) if data.token else None),
        webhook_secret=(
            encrypt_integration_secret(data.webhook_secret) if data.webhook_secret else None
        ),
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
    if data.account_email is not None:
        setting.account_email = data.account_email
    if data.token is not None:
        # Rotation: a new token replaces the previously stored encrypted value.
        setting.token_encrypted = encrypt_integration_secret(data.token) if data.token else None
    if data.webhook_secret is not None:
        setting.webhook_secret = (
            encrypt_integration_secret(data.webhook_secret) if data.webhook_secret else None
        )
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
        body, decrypt_integration_secret(setting.webhook_secret), x_hub_signature_256
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
    if not x_gitlab_token or not _verify_gitlab_token(
        decrypt_integration_secret(setting.webhook_secret), x_gitlab_token
    ):
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


# ==================== Jira webhook ====================

# Jira status *names* are configurable per project, so the stable signal is the
# status category key rather than the display name.
JIRA_CATEGORY_STATUS_MAP = {
    "new": "Open",
    "indeterminate": "In Progress",
    "done": "Closed",
}

JIRA_ISSUE_EVENTS = {"jira:issue_created", "jira:issue_updated"}


def _verify_jira_signature(body: bytes, secret: str, signature: str) -> bool:
    """Jira Cloud signs the webhook body with HMAC-SHA256 when a secret is set."""
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _split_jira_key(issue_key: str) -> Optional[tuple[str, int]]:
    """Split ``PROJ-123`` into ``("PROJ", 123)``.

    Jira identifies issues by key rather than by number, so the project key is
    stored in ``external_repo_full_name`` and the numeric part in
    ``external_issue_number`` — the same split GitLab uses for namespace and IID.
    This keeps Jira on the existing columns.
    """
    project_key, _, number = issue_key.rpartition("-")
    if not project_key or not number.isdigit():
        return None
    return project_key, int(number)


def jira_issue_key(defect_or_change) -> str:
    """Rebuild the Jira issue key from the stored repo/number pair."""
    return f"{defect_or_change.external_repo_full_name}-{defect_or_change.external_issue_number}"


async def _find_jira_target(db: AsyncSession, project_key: str, issue_number: int):
    """Resolve a Jira issue to the defect or change request tracking it."""
    defect = (
        await db.execute(
            select(Defect).where(
                Defect.external_tracker == "jira",
                Defect.external_repo_full_name == project_key,
                Defect.external_issue_number == issue_number,
            )
        )
    ).scalar_one_or_none()
    if defect is not None:
        return "defect", defect

    change = (
        await db.execute(
            select(ChangeRequest).where(
                ChangeRequest.external_tracker == "jira",
                ChangeRequest.external_repo_full_name == project_key,
                ChangeRequest.external_issue_number == issue_number,
            )
        )
    ).scalar_one_or_none()
    if change is not None:
        return "change_request", change

    return None


@router.post("/jira/webhook", status_code=200)
async def jira_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hub_signature: Optional[str] = Header(None),
    x_atlassian_webhook_identifier: Optional[str] = Header(None),
):
    body = await _read_webhook_body(request)
    payload = _json_payload(body)

    if payload.get("webhookEvent", "") not in JIRA_ISSUE_EVENTS:
        return {"status": "ignored", "reason": "not an issue event"}

    issue = payload.get("issue", {}) or {}
    fields = issue.get("fields", {}) or {}
    status = fields.get("status", {}) or {}
    category = (status.get("statusCategory", {}) or {}).get("key", "")
    issue_state = status.get("name") or category

    split = _split_jira_key(issue.get("key", "") or "")
    if not split:
        return {"status": "ignored", "reason": "missing or malformed issue key"}
    project_key, issue_number = split

    found = await _find_jira_target(db, project_key, issue_number)
    if found is None:
        raise HTTPException(status_code=404, detail="No matching webhook target.")
    kind, target = found

    # When a webhook secret is configured, a valid signature is REQUIRED —
    # a missing header must reject, otherwise omitting it bypasses auth.
    setting = (
        await db.execute(
            select(IntegrationSetting).where(
                IntegrationSetting.project_id == target.project_id,
                IntegrationSetting.tracker == "jira",
            )
        )
    ).scalar_one_or_none()
    if not setting or not setting.enabled or not setting.webhook_secret:
        raise HTTPException(status_code=403, detail="Webhook is not securely configured.")
    if not x_hub_signature or not _verify_jira_signature(
        body, decrypt_integration_secret(setting.webhook_secret), x_hub_signature
    ):
        _log_target_sync_event(
            db,
            kind,
            target.id,
            "inbound",
            "jira",
            "signature_failed",
            success=False,
            error="Missing or invalid HMAC signature",
        )
        await db.flush()
        raise HTTPException(status_code=403, detail="Invalid signature")
    if not x_atlassian_webhook_identifier:
        raise HTTPException(status_code=400, detail="Missing Jira webhook identifier.")
    if not await _reserve_webhook_delivery(db, setting, "jira", x_atlassian_webhook_identifier):
        return {"status": "duplicate", "delivery": x_atlassian_webhook_identifier}

    old_state = target.external_issue_state
    target.external_issue_state = issue_state
    target.external_last_event_at = datetime.utcnow()

    bloom_status = JIRA_CATEGORY_STATUS_MAP.get(category)
    if bloom_status and target.status != bloom_status:
        target.status = bloom_status
        if kind == "defect":
            if bloom_status == "Closed" and not target.closed_at:
                target.closed_at = datetime.utcnow()
            elif bloom_status != "Closed":
                target.closed_at = None

    _log_target_sync_event(
        db,
        kind,
        target.id,
        "inbound",
        "jira",
        payload.get("webhookEvent", "jira:issue_updated"),
        payload_summary=f"state: {old_state} -> {issue_state}",
        external_event_id=x_atlassian_webhook_identifier,
    )

    await db.flush()
    return {"status": "processed", "target": kind, "id": target.id}


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
        elif defect.external_tracker == "jira":
            await _push_to_jira(defect, setting, changed_fields)

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


# Terminal statuses across both artefact types: defects use Closed/Rejected,
# change requests add Implemented. Anything here closes the external issue.
CLOSING_BLOOM_STATUSES = {"Closed", "Rejected", "Implemented"}
# Statuses that mean the external issue should be (re)opened. Defect statuses
# first, then change-request statuses.
REOPENING_BLOOM_STATUSES = {
    "Open",
    "Triaged",
    "In Progress",
    "Resolved",
    "Verified",
    "Draft",
    "Submitted",
    "Under Review",
    "Approved",
}


async def _push_to_github(
    defect: Defect, setting: IntegrationSetting, changed_fields: dict
) -> None:
    body: dict = {}
    if "title" in changed_fields:
        body["title"] = defect.title
    if "status" in changed_fields:
        if defect.status in CLOSING_BLOOM_STATUSES:
            body["state"] = "closed"
        elif defect.status in REOPENING_BLOOM_STATUSES:
            body["state"] = "open"

    if not body:
        return

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(
            f"https://api.github.com/repos/{defect.external_repo_full_name}/issues/{defect.external_issue_number}",
            json=body,
            headers={
                "Authorization": f"Bearer {decrypt_integration_secret(setting.token_encrypted)}",
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
        if defect.status in CLOSING_BLOOM_STATUSES:
            body["state_event"] = "close"
        elif defect.status in REOPENING_BLOOM_STATUSES:
            body["state_event"] = "reopen"

    if not body:
        return

    base_url = (setting.base_url or "https://gitlab.com").rstrip("/")
    encoded = quote(defect.external_repo_full_name or "", safe="")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{base_url}/api/v4/projects/{encoded}/issues/{defect.external_issue_number}",
            json=body,
            headers={"PRIVATE-TOKEN": decrypt_integration_secret(setting.token_encrypted)},
        )
        resp.raise_for_status()


def _jira_auth_header(setting: IntegrationSetting) -> str:
    """Jira Cloud uses Basic auth over `email:api_token`."""
    if not setting.account_email:
        raise ValueError("Jira integration requires the account e-mail that owns the API token.")
    token = decrypt_integration_secret(setting.token_encrypted)
    encoded = base64.b64encode(f"{setting.account_email}:{token}".encode()).decode("ascii")
    return f"Basic {encoded}"


async def _push_to_jira(target, setting: IntegrationSetting, changed_fields: dict) -> None:
    """Push a title and/or status change to the linked Jira issue.

    Jira does not accept a status as a field write: the status is reached by
    applying a transition, and transition ids differ per workflow. So the status
    path reads the issue's available transitions and picks the one landing in the
    wanted status category.
    """
    if not setting.base_url:
        raise ValueError("Jira integration requires the site base URL.")

    issue_key = jira_issue_key(target)
    base_url = setting.base_url.rstrip("/")
    headers = {
        "Authorization": _jira_auth_header(setting),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        if "title" in changed_fields:
            resp = await client.put(
                f"{base_url}/rest/api/3/issue/{issue_key}",
                json={"fields": {"summary": target.title}},
                headers=headers,
            )
            resp.raise_for_status()

        if "status" not in changed_fields:
            return

        if target.status in CLOSING_BLOOM_STATUSES:
            wanted = "done"
        elif target.status in REOPENING_BLOOM_STATUSES:
            wanted = "new"
        else:
            return

        resp = await client.get(
            f"{base_url}/rest/api/3/issue/{issue_key}/transitions", headers=headers
        )
        resp.raise_for_status()
        transitions = resp.json().get("transitions", []) or []

        transition_id = next(
            (
                t.get("id")
                for t in transitions
                if ((t.get("to", {}) or {}).get("statusCategory", {}) or {}).get("key") == wanted
            ),
            None,
        )
        if transition_id is None:
            raise ValueError(
                f"No Jira transition on {issue_key} reaches the '{wanted}' status category."
            )

        resp = await client.post(
            f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
            json={"transition": {"id": transition_id}},
            headers=headers,
        )
        resp.raise_for_status()


async def sync_change_request_to_tracker(
    db: AsyncSession,
    change_request: ChangeRequest,
    changed_fields: dict,
) -> None:
    """Push change request updates to the linked external tracker if configured."""
    if not change_request.external_tracker or not change_request.external_repo_full_name:
        return

    setting = (
        await db.execute(
            select(IntegrationSetting).where(
                IntegrationSetting.project_id == change_request.project_id,
                IntegrationSetting.tracker == change_request.external_tracker,
                IntegrationSetting.enabled == True,  # noqa: E712
            )
        )
    ).scalar_one_or_none()

    if not setting or not setting.token_encrypted:
        return

    try:
        if change_request.external_tracker == "github":
            await _push_to_github(change_request, setting, changed_fields)
        elif change_request.external_tracker == "gitlab":
            await _push_to_gitlab(change_request, setting, changed_fields)
        elif change_request.external_tracker == "jira":
            await _push_to_jira(change_request, setting, changed_fields)

        _log_change_request_sync_event(
            db,
            change_request.id,
            "outbound",
            change_request.external_tracker,
            "update_pushed",
            payload_summary=f"fields: {', '.join(changed_fields.keys())}",
        )
        change_request.external_last_event_at = datetime.utcnow()
    except Exception as exc:
        logger.warning("Outbound sync failed for change request %s: %s", change_request.id, exc)
        _log_change_request_sync_event(
            db,
            change_request.id,
            "outbound",
            change_request.external_tracker,
            "update_failed",
            success=False,
            error=str(exc),
        )


# ==================== Helpers ====================


def _log_target_sync_event(
    db: AsyncSession,
    kind: str,
    target_id: int,
    direction: str,
    tracker: str,
    event_type: str,
    payload_summary: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None,
    external_event_id: Optional[str] = None,
) -> None:
    """Route a sync event to the defect or change-request log."""
    log = _log_sync_event if kind == "defect" else _log_change_request_sync_event
    log(
        db,
        target_id,
        direction,
        tracker,
        event_type,
        payload_summary=payload_summary,
        success=success,
        error=error,
        external_event_id=external_event_id,
    )


def _log_change_request_sync_event(
    db: AsyncSession,
    change_request_id: int,
    direction: str,
    tracker: str,
    event_type: str,
    payload_summary: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None,
    external_event_id: Optional[str] = None,
) -> None:
    db.add(
        ChangeRequestSyncEvent(
            change_request_id=change_request_id,
            direction=direction,
            tracker=tracker,
            event_type=event_type,
            payload_summary=payload_summary,
            success=success,
            error_message=error,
            external_event_id=external_event_id,
        )
    )


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
