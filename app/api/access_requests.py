"""Access requests: a signed-in user who is refused a resource asks the administrators.

The request names the resource by the type, reference and project prefix the user saw in
the address. A user who can open the resource, and every administrator, is refused with
409. The requester sees the resource only as the address named it, unless they can open
it; administrators see its document ID or project prefix. One request per user and resource
per 24 hours; the other administrators are emailed and the request, its grant or its refusal
are recorded in the audit log.
"""

from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import minute_utc
from app.api.docs_facade import TYPE_MAP, find_visible_doc, resolve_project
from app.core.config import settings
from app.core.database import get_db
from app.core.document_kinds import DOCUMENT_KIND_SLUGS
from app.core.observability import request_id_var
from app.core.security import get_current_user, require_project_access, require_role
from app.models.access_request import AccessRequest
from app.models.user import User, UserRole
from app.services.audit import record_audit_event
from app.services.mail_service import MailConfigurationError, send_access_request_email

router = APIRouter()

require_admin = require_role(UserRole.admin)

REQUEST_WINDOW = timedelta(hours=24)

ResourceType = Literal[
    "project",
    "requirement",
    "test-case",
    "design",
    "risk",
    "change",
    "test-concept",
    "defect",
    "document",
    "test-suite",
    "campaign",
]


ITEM_KIND_SLUGS: dict[str, tuple[str, ...]] = {
    "requirement": ("requirements",),
    "test-case": ("test-cases",),
    "design": ("designs",),
    "risk": ("risks",),
    "change": ("changes",),
    "test-concept": ("test-concepts",),
    "defect": ("defects",),
    "test-suite": ("test-suites",),
    "campaign": ("campaigns",),
    "document": tuple(DOCUMENT_KIND_SLUGS.values())
    + tuple(slug for _model, _column, slug in TYPE_MAP.values()),
}


class AccessRequestCreate(BaseModel):
    """What the user asks access to, as shown in the address they opened."""

    resource_type: ResourceType
    resource_ref: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    project_prefix: Optional[str] = Field(
        None, min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_-]+$"
    )


class AccessRequestResponse(BaseModel):
    """A request, as its requester or an administrator sees it."""

    id: int
    resource_type: str
    resource_ref: str
    project_prefix: Optional[str] = None
    resource_label: Optional[str] = None
    status: str
    created_at: datetime
    decided_at: Optional[datetime] = None
    requester_name: Optional[str] = None
    requester_email: Optional[str] = None
    requester_profile_picture_url: Optional[str] = None
    already_requested: bool = False
    mail_sent: Optional[bool] = None

    @field_serializer("created_at", "decided_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None


class AccessDecision(BaseModel):
    """An administrator's answer to a pending request."""

    decision: Literal["granted", "refused"]


async def open_label(
    db: AsyncSession,
    viewer: User,
    resource_type: str,
    resource_ref: str,
    project_prefix: Optional[str],
) -> Optional[str]:
    """The project prefix or document ID of the resource when the viewer can open it, else None.

    A number names an item by its database id; for the generic document type every kind with an
    item of that id is named.
    """
    if resource_type != "project" and not project_prefix:
        return None
    try:
        project = await resolve_project(db, project_prefix or resource_ref)
        await require_project_access(db, viewer, project.id)
    except HTTPException:
        return None
    if resource_type == "project":
        return project.prefix
    labels = []
    for slug in ITEM_KIND_SLUGS.get(resource_type, ()):
        try:
            found = await find_visible_doc(
                db, viewer, project, slug, resource_ref, record_refusals=False
            )
        except HTTPException:
            found = None
        if found is not None:
            _model, row, _type, id_column = found
            labels.append(str(getattr(row, id_column) or row.id))
            if not resource_ref.isdigit():
                break
    return " or ".join(sorted(set(labels))) or None


def unresolved_label(resource_ref: str) -> str:
    """A reference that names nothing that exists: a number is marked deleted."""
    return f"{resource_ref} (deleted)" if resource_ref.isdigit() else f"{resource_ref} (not found)"


async def admin_label(db: AsyncSession, admin: User, row: AccessRequest) -> str:
    """The resource of a request as an administrator sees it."""
    label = await open_label(db, admin, row.resource_type, row.resource_ref, row.project_prefix)
    return label or unresolved_label(row.resource_ref)


async def requester_label(db: AsyncSession, requester: User, row: AccessRequest) -> str:
    """The resource of a request as its requester sees it: the address's reference, or the
    document ID once they can open it."""
    label = await open_label(db, requester, row.resource_type, row.resource_ref, row.project_prefix)
    return label or row.resource_ref


def _response(
    row: AccessRequest, user: Optional[User] = None, label: Optional[str] = None, **extra
) -> AccessRequestResponse:
    return AccessRequestResponse(
        id=row.id,
        resource_type=row.resource_type,
        resource_ref=row.resource_ref,
        resource_label=label,
        project_prefix=row.project_prefix,
        status=row.status,
        created_at=row.created_at,
        decided_at=row.decided_at,
        requester_name=user.full_name if user else None,
        requester_email=user.email if user else None,
        requester_profile_picture_url=user.profile_picture_url if user else None,
        **extra,
    )


async def _recent_request(
    db: AsyncSession,
    user_id: int,
    resource_type: str,
    resource_ref: str,
    project_prefix: Optional[str],
) -> Optional[AccessRequest]:
    """The user's request for this resource from the last 24 hours, if any."""
    query = (
        select(AccessRequest)
        .where(
            AccessRequest.user_id == user_id,
            AccessRequest.resource_type == resource_type,
            AccessRequest.resource_ref == resource_ref,
            AccessRequest.created_at
            >= datetime.now(timezone.utc).replace(tzinfo=None) - REQUEST_WINDOW,
        )
        .order_by(AccessRequest.created_at.desc())
        .limit(1)
    )
    if project_prefix is None:
        query = query.where(AccessRequest.project_prefix.is_(None))
    else:
        query = query.where(AccessRequest.project_prefix == project_prefix)
    return (await db.execute(query)).scalar_one_or_none()


def _review_link(project_prefix: Optional[str]) -> str:
    """Where an administrator grants the access: the project's members, or the users."""
    base = settings.APP_BASE_URL.rstrip("/")
    return f"{base}/projects/{project_prefix}/edit" if project_prefix else f"{base}/users"


@router.post(
    "",
    response_model=AccessRequestResponse,
    status_code=201,
    responses={409: {"description": HTTPStatus(409).phrase}},
)
async def request_access(
    data: AccessRequestCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Ask the administrators for access; a repeat within 24 hours returns the first request.

    An administrator, or a user who can open the resource, gets 409 and nothing is recorded or
    sent.
    """
    if current_user.role == UserRole.admin:
        raise HTTPException(
            status_code=409,
            detail="Administrators hold every access, so there is nothing to request.",
        )
    held = await open_label(
        db, current_user, data.resource_type, data.resource_ref, data.project_prefix
    )
    if held is not None:
        raise HTTPException(status_code=409, detail=f"You already have access to {held}.")
    existing = await _recent_request(
        db, current_user.id, data.resource_type, data.resource_ref, data.project_prefix
    )
    if existing is not None:
        response.status_code = 200
        return _response(existing, label=existing.resource_ref, already_requested=True)

    row = AccessRequest(
        user_id=current_user.id,
        resource_type=data.resource_type,
        resource_ref=data.resource_ref,
        project_prefix=data.project_prefix,
        status="pending",
    )
    db.add(row)
    await db.flush()
    await record_audit_event(
        db,
        "access.requested",
        target_type=data.resource_type,
        target_id=data.resource_ref,
        details={"project_prefix": data.project_prefix, "access_request_id": row.id},
    )

    admins = (
        (
            await db.execute(
                select(User).where(
                    User.role == UserRole.admin,
                    User.is_active.is_(True),
                    User.id != current_user.id,
                )
            )
        )
        .scalars()
        .all()
    )
    resource = await admin_label(db, admins[0], row) if admins else data.resource_ref
    mail_sent = bool(admins)
    for admin in admins:
        try:
            send_access_request_email(
                to_email=admin.email,
                admin_name=admin.full_name,
                requester_name=current_user.full_name,
                requester_email=current_user.email,
                resource=resource,
                project=data.project_prefix or "",
                requested_at=minute_utc(row.created_at),
                request_id=request_id_var.get(),
                review_link=_review_link(data.project_prefix),
            )
        except MailConfigurationError:
            mail_sent = False
    return _response(row, label=data.resource_ref, mail_sent=mail_sent)


@router.get("/mine", response_model=Optional[AccessRequestResponse])
async def my_access_request(
    resource_type: ResourceType,
    resource_ref: str = Query(..., min_length=1, max_length=100),
    project_prefix: Optional[str] = Query(None, max_length=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """The user's own request for this resource from the last 24 hours, or null."""
    row = await _recent_request(db, current_user.id, resource_type, resource_ref, project_prefix)
    if row is None:
        return None
    return _response(
        row, label=await requester_label(db, current_user, row), already_requested=True
    )


@router.get("", response_model=list[AccessRequestResponse])
async def list_access_requests(
    status: Optional[Literal["pending", "granted", "refused"]] = "pending",
    project_prefix: Optional[str] = Query(None, max_length=20),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Access requests for administrators, newest first, each resource by its document ID or
    project prefix."""
    query = (
        select(AccessRequest, User)
        .join(User, User.id == AccessRequest.user_id)
        .order_by(AccessRequest.created_at.desc())
    )
    if status:
        query = query.where(AccessRequest.status == status)
    if project_prefix:
        query = query.where(AccessRequest.project_prefix == project_prefix)
    return [
        _response(row, user, await admin_label(db, admin, row))
        for row, user in (await db.execute(query)).all()
    ]


@router.post(
    "/{request_id}/decision",
    response_model=AccessRequestResponse,
    responses={
        404: {"description": HTTPStatus(404).phrase},
        409: {"description": HTTPStatus(409).phrase},
    },
)
async def decide_access_request(
    request_id: int,
    data: AccessDecision,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Record the administrator's grant or refusal against a pending request."""
    row = await db.get(AccessRequest, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Access request not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail="This request was already answered")
    row.status = data.decision
    row.decided_by_user_id = admin.id
    row.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await record_audit_event(
        db,
        f"access.{data.decision}",
        target_type=row.resource_type,
        target_id=row.resource_ref,
        details={
            "project_prefix": row.project_prefix,
            "access_request_id": row.id,
            "requester_user_id": row.user_id,
        },
    )
    requester = await db.get(User, row.user_id)
    return _response(row, requester, await admin_label(db, admin, row))
