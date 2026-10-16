"""
Users API endpoints (admin only): CRUD for user management.
"""

import secrets
import string
from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import get_row_or_404
from app.api.groups import _selected_policies
from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import as_lists
from app.core.security import (
    effective_permissions,
    get_current_user,
    get_password_hash,
    require_project_access,
    require_role,
)
from app.models import Project, ReportRequest
from app.models.groups import GroupMembership, user_application_policies
from app.models.models import (
    ARTEFACT_MODELS,
    Defect,
    DocumentAttachment,
    ImportAttempt,
    Notification,
    Requirement,
    ServiceCredential,
    TestCase,
)
from app.models.project_membership import (
    ProjectAccess,
    ProjectExternalDocType,
    ProjectMembership,
)
from app.models.user import User, UserRole
from app.models.user_token import UserToken, UserTokenPurpose
from app.schemas.auth import (
    AdminEmailChangeRequest,
    InviteCreateRequest,
    InviteResponse,
    MentionableUserResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.audit import record_audit_event
from app.services.mail_service import (
    MailConfigurationError,
    send_email_change_email,
    send_invite_email,
)
from app.services.token_service import create_user_token, invalidate_tokens

USER_NOT_FOUND = "User not found"

router = APIRouter()

require_admin = require_role(UserRole.admin)


class ApplicationPoliciesInput(BaseModel):
    """The distinct application policies assigned to one account."""

    model_config = ConfigDict(extra="forbid")
    policy_ids: list[int] = Field(default_factory=list)

    @field_validator("policy_ids")
    @classmethod
    def valid_ids(cls, ids):
        """Require distinct positive policy identifiers."""
        if any(value <= 0 for value in ids) or len(ids) != len(set(ids)):
            raise ValueError("Choose distinct positive policy identifiers")
        return sorted(ids)


@router.get("/me/application-permissions")
async def my_application_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Return the current account's app-resource operations."""
    return as_lists(await effective_permissions(db, current_user, None))


@router.get(
    "/{user_id}/application-policies", responses={404: {"description": HTTPStatus(404).phrase}}
)
async def application_policy_ids(
    user_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """List the account's separately selected application policies."""
    if await db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    ids = await db.scalars(
        select(user_application_policies.c.policy_id)
        .where(user_application_policies.c.user_id == user_id)
        .order_by(user_application_policies.c.policy_id)
    )
    return {"policy_ids": list(ids)}


@router.put(
    "/{user_id}/application-policies",
    responses={
        400: {"description": HTTPStatus(400).phrase},
        404: {"description": HTTPStatus(404).phrase},
    },
)
async def set_application_policies(
    user_id: int,
    data: ApplicationPoliciesInput,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Set app-only policies for an account without changing its base role."""
    if await db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    policies = await _selected_policies(db, data.policy_ids)
    if any(policy.scope != "app" for policy in policies):
        raise HTTPException(status_code=400, detail="Choose application policies only")
    existing = set(
        await db.scalars(
            select(user_application_policies.c.policy_id).where(
                user_application_policies.c.user_id == user_id
            )
        )
    )
    removed = existing - set(data.policy_ids)
    if removed:
        await db.execute(
            delete(user_application_policies).where(
                user_application_policies.c.user_id == user_id,
                user_application_policies.c.policy_id.in_(removed),
            )
        )
    added = set(data.policy_ids) - existing
    if added:
        await db.execute(
            user_application_policies.insert(),
            [{"user_id": user_id, "policy_id": policy_id} for policy_id in sorted(added)],
        )
    await record_audit_event(
        db,
        "user.application_policies_updated",
        target_type="user",
        target_id=user_id,
        details={"policy_ids": data.policy_ids},
    )
    return {"policy_ids": data.policy_ids}


async def _get_user_or_404(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id, populate_existing=True, with_for_update=True)
    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    return user


async def _validate_new_email(db: AsyncSession, user: User, new_email: str) -> None:
    if new_email == user.email:
        raise HTTPException(status_code=400, detail="New email matches the current email")
    existing = await db.execute(select(User).where(User.email == new_email, User.id != user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already in use")


async def _send_email_change_confirmation(
    db: AsyncSession,
    *,
    user: User,
    new_email: str,
    admin: User,
    action: str,
) -> UserResponse:
    await _validate_new_email(db, user, new_email)
    await invalidate_tokens(db, user.id, purpose=UserTokenPurpose.email_change)

    user.pending_email = new_email
    user.email_change_status = "awaiting_confirmation"
    user.email_change_requested_at = user.email_change_requested_at or datetime.now(
        timezone.utc
    ).replace(tzinfo=None)
    token = await create_user_token(
        db,
        user_id=user.id,
        purpose=UserTokenPurpose.email_change,
        ttl_hours=settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS,
        created_by_user_id=admin.id,
        target_email=new_email,
    )
    confirm_link = f"{settings.APP_BASE_URL.rstrip('/')}/confirm-email-change#token={token}"
    try:
        send_email_change_email(
            to_email=new_email,
            full_name=user.full_name,
            old_email=user.email,
            new_email=new_email,
            confirm_link=confirm_link,
        )
    except MailConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    await record_audit_event(
        db,
        action,
        target_type="user",
        target_id=user.id,
        details={"new_email": new_email},
    )
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("", response_model=list[UserResponse])
async def list_users(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


# Declared before GET /{user_id}, or "mentionable" is parsed as a user id.
@router.get("/mentionable", response_model=list[MentionableUserResponse])
async def list_mentionable_users(
    project_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Who may be addressed with `@` in one project."""
    await get_row_or_404(db, Project, project_id, "Project not found")

    await require_project_access(db, current_user, project_id)

    member_ids = select(ProjectAccess.user_id).where(ProjectAccess.project_id == project_id)
    grouped_ids = select(GroupMembership.user_id).where(
        GroupMembership.group_id.in_(
            select(ProjectAccess.group_id).where(ProjectAccess.project_id == project_id)
        )
    )
    result = await db.execute(
        select(User)
        .where(User.is_active.is_(True))
        .where(or_(User.id.in_(member_ids), User.id.in_(grouped_ids), User.role == UserRole.admin))
        .order_by(User.full_name.asc())
    )
    return [MentionableUserResponse.model_validate(u) for u in result.scalars().all()]


@router.post(
    "",
    response_model=UserResponse,
    status_code=201,
    responses={400: {"description": "Bad Request"}},
)
async def create_user(
    data: UserCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        role=data.role,
    )
    db.add(user)
    await db.flush()
    await record_audit_event(
        db,
        "user.created",
        target_type="user",
        target_id=user.id,
        details={"email": user.email, "role": user.role.value},
    )
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post(
    "/invite",
    response_model=InviteResponse,
    status_code=201,
    responses={400: {"description": "Bad Request"}, 503: {"description": "Service Unavailable"}},
)
async def invite_user(
    data: InviteCreateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    existing = await db.execute(select(User).where(User.email == data.email))
    user = existing.scalar_one_or_none()

    if user and user.password_set_at is not None:
        raise HTTPException(status_code=400, detail="Email already belongs to an active user")

    alphabet = string.ascii_letters + string.digits
    temp_password = "".join(secrets.choice(alphabet) for _ in range(12))

    if user is None:
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=get_password_hash(temp_password),
            role=data.role,
            is_active=True,
            invited_at=datetime.now(timezone.utc).replace(tzinfo=None),
            invited_by_user_id=admin.id,
            last_invite_sent_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(user)
        await db.flush()
    else:
        user.full_name = data.full_name
        user.role = data.role
        user.hashed_password = get_password_hash(temp_password)
        user.invited_at = user.invited_at or datetime.now(timezone.utc).replace(tzinfo=None)
        user.invited_by_user_id = admin.id
        user.last_invite_sent_at = datetime.now(timezone.utc).replace(tzinfo=None)

    invite_token = await create_user_token(
        db,
        user_id=user.id,
        purpose=UserTokenPurpose.invite,
        ttl_hours=settings.INVITE_TOKEN_TTL_HOURS,
        created_by_user_id=admin.id,
    )
    invite_link = f"{settings.APP_BASE_URL.rstrip('/')}/accept-invite#token={invite_token}"

    try:
        send_invite_email(
            to_email=user.email,
            full_name=user.full_name,
            invite_link=invite_link,
        )
    except MailConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    await record_audit_event(
        db,
        "user.invited",
        target_type="user",
        target_id=user.id,
        details={"email": user.email, "role": user.role.value},
    )
    await db.refresh(user)
    return InviteResponse(
        message="Invitation sent",
        user=UserResponse.model_validate(user),
        invite_link=invite_link,
    )


@router.post(
    "/{user_id}/resend-invite",
    response_model=InviteResponse,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        503: {"description": "Service Unavailable"},
    },
)
async def resend_invite(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    if user.password_set_at is not None:
        raise HTTPException(status_code=400, detail="Invite already accepted")

    user.last_invite_sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
    alphabet = string.ascii_letters + string.digits
    temp_password = "".join(secrets.choice(alphabet) for _ in range(12))
    user.hashed_password = get_password_hash(temp_password)
    invite_token = await create_user_token(
        db,
        user_id=user.id,
        purpose=UserTokenPurpose.invite,
        ttl_hours=settings.INVITE_TOKEN_TTL_HOURS,
        created_by_user_id=admin.id,
    )
    invite_link = f"{settings.APP_BASE_URL.rstrip('/')}/accept-invite#token={invite_token}"

    try:
        send_invite_email(
            to_email=user.email,
            full_name=user.full_name,
            invite_link=invite_link,
        )
    except MailConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    await record_audit_event(db, "user.invite_resent", target_type="user", target_id=user.id)
    await db.refresh(user)
    return InviteResponse(
        message="Invitation resent",
        user=UserResponse.model_validate(user),
        invite_link=invite_link,
    )


@router.post(
    "/{user_id}/revoke-invite",
    response_model=InviteResponse,
    responses={400: {"description": "Bad Request"}, 404: {"description": "Not Found"}},
)
async def revoke_invite(
    user_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    if user.password_set_at is not None:
        raise HTTPException(status_code=400, detail="Invite already accepted")

    user.is_active = False
    await record_audit_event(db, "user.invite_revoked", target_type="user", target_id=user.id)
    await db.refresh(user)
    return InviteResponse(message="Invitation revoked", user=UserResponse.model_validate(user))


@router.get(
    "/{user_id}", response_model=UserResponse, responses={404: {"description": "Not Found"}}
)
async def get_user(
    user_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    return UserResponse.model_validate(user)


@router.post("/{user_id}/email", response_model=UserResponse)
async def start_email_change(
    user_id: int,
    data: AdminEmailChangeRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Start the verified email-change workflow for a user."""
    user = await _get_user_or_404(db, user_id)
    user.email_change_requested_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return await _send_email_change_confirmation(
        db,
        user=user,
        new_email=str(data.new_email),
        admin=admin,
        action="user.email_change_started",
    )


@router.post(
    "/{user_id}/email/approve",
    response_model=UserResponse,
    responses={400: {"description": "Bad Request"}},
)
async def approve_email_change(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    user = await _get_user_or_404(db, user_id)
    if not user.pending_email or user.email_change_status != "requested":
        raise HTTPException(
            status_code=400,
            detail="No email change request is waiting for administrator approval",
        )
    return await _send_email_change_confirmation(
        db,
        user=user,
        new_email=user.pending_email,
        admin=admin,
        action="user.email_change_approved",
    )


@router.delete(
    "/{user_id}/email", response_model=UserResponse, responses={400: {"description": "Bad Request"}}
)
async def reject_email_change(
    user_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    user = await _get_user_or_404(db, user_id)
    if not user.pending_email:
        raise HTTPException(status_code=400, detail="No pending email change")
    user.pending_email = None
    user.email_change_status = None
    user.email_change_requested_at = None
    await invalidate_tokens(db, user.id, purpose=UserTokenPurpose.email_change)
    await record_audit_event(
        db, "user.email_change_rejected", target_type="user", target_id=user.id
    )
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    responses={
        403: {"description": HTTPStatus(403).phrase},
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
    },
)
async def update_user(
    user_id: int,
    data: UserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    previous_role = user.role
    previous_active = user.is_active
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        if user.role == UserRole.admin and data.role != UserRole.admin:
            raise HTTPException(status_code=400, detail="Admin role cannot be changed")
        if user.role != UserRole.admin and data.role == UserRole.admin:
            if admin.email != settings.ADMIN_EMAIL:
                raise HTTPException(
                    status_code=403,
                    detail="Only the initial administrator can promote users to admin",
                )
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active

    if user.role != previous_role:
        await record_audit_event(
            db,
            "user.role_changed",
            target_type="user",
            target_id=user.id,
            details={"from": previous_role.value, "to": user.role.value},
        )
    if user.is_active != previous_active:
        await record_audit_event(
            db,
            "user.activated" if user.is_active else "user.deactivated",
            target_type="user",
            target_id=user.id,
        )
    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=204,
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        409: {"description": "Conflict"},
    },
)
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    if admin.id == user_id:
        raise HTTPException(
            status_code=400,
            detail="Admin users cannot delete their own account",
        )

    try:
        await db.execute(delete(ReportRequest).where(ReportRequest.requester_id == user_id))
        await db.execute(delete(UserToken).where(UserToken.user_id == user_id))
        await db.execute(
            update(UserToken)
            .where(UserToken.created_by_user_id == user_id)
            .values(created_by_user_id=None)
        )
        await db.execute(
            update(User).where(User.invited_by_user_id == user_id).values(invited_by_user_id=None)
        )

        await db.execute(
            update(Requirement).where(Requirement.reviewer_id == user_id).values(reviewer_id=None)
        )
        await db.execute(
            update(Requirement).where(Requirement.approver_id == user_id).values(approver_id=None)
        )
        await db.execute(
            update(Requirement)
            .where(Requirement.reviewed_by_id == user_id)
            .values(reviewed_by_id=None, reviewed_at=None)
        )
        await db.execute(
            update(Requirement)
            .where(Requirement.approved_by_id == user_id)
            .values(approved_by_id=None, approved_at=None)
        )

        await db.execute(
            update(TestCase).where(TestCase.reviewer_id == user_id).values(reviewer_id=None)
        )
        await db.execute(
            update(TestCase).where(TestCase.approver_id == user_id).values(approver_id=None)
        )
        await db.execute(
            update(TestCase)
            .where(TestCase.reviewed_by_id == user_id)
            .values(reviewed_by_id=None, reviewed_at=None)
        )
        await db.execute(
            update(TestCase)
            .where(TestCase.approved_by_id == user_id)
            .values(approved_by_id=None, approved_at=None)
        )

        # Rows that cannot exist without their user.
        await db.execute(
            delete(ProjectExternalDocType).where(
                ProjectExternalDocType.membership_id.in_(
                    select(ProjectMembership.id).where(ProjectMembership.user_id == user_id)
                )
            )
        )
        await db.execute(delete(ProjectMembership).where(ProjectMembership.user_id == user_id))
        await db.execute(delete(ProjectAccess).where(ProjectAccess.user_id == user_id))
        await db.execute(delete(GroupMembership).where(GroupMembership.user_id == user_id))
        await db.execute(delete(Notification).where(Notification.user_id == user_id))
        await db.execute(delete(ImportAttempt).where(ImportAttempt.user_id == user_id))

        # A service credential outlives whoever minted it: deleting one because
        # its creator left would silently break a working integration, so it is
        # reassigned to the administrator performing the deletion instead.
        await db.execute(
            update(ServiceCredential)
            .where(ServiceCredential.created_by_user_id == user_id)
            .values(created_by_user_id=admin.id)
        )

        await db.execute(update(Defect).where(Defect.owner_id == user_id).values(owner_id=None))
        await db.execute(
            update(Defect).where(Defect.reporter_id == user_id).values(reporter_id=None)
        )
        await db.execute(
            update(Defect).where(Defect.reviewer_id == user_id).values(reviewer_id=None)
        )
        await db.execute(
            update(DocumentAttachment)
            .where(DocumentAttachment.uploaded_by_id == user_id)
            .values(uploaded_by_id=None)
        )

        for model in ARTEFACT_MODELS:
            await db.execute(
                update(model).where(model.created_by_id == user_id).values(created_by_id=None)
            )

        deleted_email = user.email
        await db.delete(user)

        # Force the statement out now.
        await db.flush()
        await record_audit_event(
            db,
            "user.deleted",
            target_type="user",
            target_id=user_id,
            details={"email": deleted_email},
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="User could not be deleted because related records still reference this account",
        ) from exc
