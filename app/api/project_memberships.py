"""Administrator-managed direct user entries and project access provenance."""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.groups import _selected_policies
from app.core.database import get_db
from app.core.permissions import as_lists
from app.core.security import (
    effective_permissions,
    get_current_user,
    require_app_permission,
)
from app.models import Project
from app.models.groups import Group, GroupMembership
from app.models.project_membership import ProjectAccess
from app.models.user import User, UserRole
from app.schemas.memberships import (
    ProjectMemberResponse,
    ProjectMembershipCreate,
    ProjectMembershipUpdate,
    validate_entry,
)
from app.services.audit import record_audit_event

router = APIRouter()
require_admin = require_app_permission("view")


async def _project(db: AsyncSession, project_id: int, lock: bool = False) -> None:
    """Require a project and optionally serialize changes to its access entries."""
    statement = select(Project.id).where(Project.id == project_id)
    if lock:
        statement = statement.with_for_update()
    if await db.scalar(statement) is None:
        raise HTTPException(status_code=404, detail="Project not found")


async def _check_direct_conflict(
    db: AsyncSession,
    project_id: int,
    user_id: int,
    policy_group_id: int | None,
    entry_id: int | None = None,
) -> None:
    """Reject duplicate bundles and mixed individual and bundle assignments."""
    statement = select(ProjectAccess.id).where(
        ProjectAccess.project_id == project_id, ProjectAccess.user_id == user_id
    )
    if entry_id is not None:
        statement = statement.where(ProjectAccess.id != entry_id)
    if policy_group_id is not None:
        statement = statement.where(
            or_(
                ProjectAccess.policy_group_id.is_(None),
                ProjectAccess.policy_group_id == policy_group_id,
            )
        )
    if await db.scalar(statement.limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Conflicting direct project assignment")


async def _entry(db: AsyncSession, project_id: int, entry_id: int) -> ProjectAccess:
    """Find a direct user entry within the addressed project."""
    row = await db.scalar(
        select(ProjectAccess).where(
            ProjectAccess.id == entry_id,
            ProjectAccess.project_id == project_id,
            ProjectAccess.user_id.is_not(None),
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    return row


async def _response(db: AsyncSession, entry: ProjectAccess) -> ProjectMemberResponse:
    """Describe the direct entry and its user without a role baseline."""
    user = await db.get(User, entry.user_id)
    group = await db.get(Group, entry.policy_group_id) if entry.policy_group_id else None
    return ProjectMemberResponse(
        id=entry.id,
        user_id=entry.user_id,
        email=user.email,
        full_name=user.full_name,
        profile_picture_url=user.profile_picture_url,
        owner=entry.owner,
        inherit_policies=entry.inherit_policies,
        policy_ids=sorted(policy.id for policy in (group.policies if group else entry.policies)),
        policy_group_id=entry.policy_group_id,
        policy_group_name=group.name if group else None,
        created_at=entry.created_at,
    )


async def _selected_group(db: AsyncSession, group_id: int) -> Group:
    """Resolve a nonempty project policy bundle."""
    group = await db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    if not group.policies:
        raise HTTPException(status_code=400, detail="Choose a group with policies")
    return group


@router.get(
    "/{project_id}/members",
    response_model=list[ProjectMemberResponse],
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def list_project_members(
    project_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """List the project's direct user entries."""
    await _project(db, project_id)
    rows = (
        (
            await db.execute(
                select(ProjectAccess)
                .where(ProjectAccess.project_id == project_id, ProjectAccess.user_id.is_not(None))
                .order_by(ProjectAccess.id)
            )
        )
        .scalars()
        .all()
    )
    return [await _response(db, row) for row in rows]


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=201,
    responses={
        400: {"description": HTTPStatus(400).phrase},
        404: {"description": HTTPStatus(404).phrase},
        409: {"description": HTTPStatus(409).phrase},
    },
)
async def add_project_member(
    project_id: int,
    data: ProjectMembershipCreate,
    _admin: User = Depends(require_app_permission("create")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Assign Owner or explicitly selected policies to a user on this project."""
    await _project(db, project_id, lock=True)
    user = await db.get(User, data.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Admin users do not need project memberships")
    await _check_direct_conflict(db, project_id, data.user_id, data.policy_group_id)
    if data.policy_group_id is not None:
        await _selected_group(db, data.policy_group_id)
    policies = await _selected_policies(db, data.policy_ids)
    if any(policy.scope == "app" for policy in policies):
        raise HTTPException(
            status_code=400, detail="Application policies cannot be assigned on a project"
        )
    entry = ProjectAccess(
        project_id=project_id,
        user_id=data.user_id,
        owner=data.owner,
        inherit_policies=data.inherit_policies,
        policies=policies,
        policy_group_id=data.policy_group_id,
    )
    db.add(entry)
    await db.flush()
    await record_audit_event(
        db,
        "project_member.added",
        target_type="user",
        target_id=user.id,
        project_id=project_id,
        details={
            "membership_id": entry.id,
            "policy_group_id": entry.policy_group_id,
            "owner": entry.owner,
            "policy_ids": sorted(data.policy_ids),
        },
    )
    return await _response(db, entry)


@router.get(
    "/{project_id}/members/{membership_id}",
    response_model=ProjectMemberResponse,
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def get_project_member(
    project_id: int,
    membership_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Read a direct user entry of this project."""
    return await _response(db, await _entry(db, project_id, membership_id))


@router.patch(
    "/{project_id}/members/{membership_id}",
    response_model=ProjectMemberResponse,
    responses={
        400: {"description": HTTPStatus(400).phrase},
        404: {"description": HTTPStatus(404).phrase},
        422: {"description": HTTPStatus(422).phrase},
        409: {"description": HTTPStatus(409).phrase},
    },
)
async def update_project_member(
    project_id: int,
    membership_id: int,
    data: ProjectMembershipUpdate,
    _admin: User = Depends(require_app_permission("edit")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Update a direct entry without inheriting a role baseline."""
    await _project(db, project_id, lock=True)
    entry = await _entry(db, project_id, membership_id)
    owner = data.owner if data.owner is not None else entry.owner
    inherit_policies = (
        data.inherit_policies if data.inherit_policies is not None else entry.inherit_policies
    )
    policy_ids = (
        data.policy_ids if data.policy_ids is not None else [policy.id for policy in entry.policies]
    )
    policy_group_id = (
        data.policy_group_id
        if "policy_group_id" in data.model_fields_set
        else entry.policy_group_id
    )
    if data.policy_group_id is not None:
        if data.owner or data.inherit_policies or data.policy_ids:
            raise HTTPException(status_code=422, detail="Choose only a project policy group")
        await _selected_group(db, data.policy_group_id)
        owner, inherit_policies, policy_ids = False, False, []
    elif any(key in data.model_fields_set for key in ("owner", "inherit_policies", "policy_ids")):
        policy_group_id = None
    try:
        validate_entry(owner, policy_ids, inherit_policies, policy_group_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    await _check_direct_conflict(db, project_id, entry.user_id, policy_group_id, entry.id)
    policies = await _selected_policies(db, policy_ids)
    if any(policy.scope == "app" for policy in policies):
        raise HTTPException(
            status_code=400, detail="Application policies cannot be assigned on a project"
        )
    previous_policy_group_id = entry.policy_group_id
    entry.policy_group_id = policy_group_id
    entry.owner = owner
    entry.inherit_policies = inherit_policies
    entry.policies = policies
    await db.flush()
    await record_audit_event(
        db,
        "project_member.updated",
        target_type="user",
        target_id=entry.user_id,
        project_id=project_id,
        details={
            "membership_id": entry.id,
            "policy_group_id": entry.policy_group_id,
            "previous_policy_group_id": previous_policy_group_id,
            "owner": owner,
            "policy_ids": sorted(policy_ids),
        },
    )
    return await _response(db, entry)


@router.delete(
    "/{project_id}/members/{membership_id}",
    status_code=204,
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def remove_project_member(
    project_id: int,
    membership_id: int,
    _admin: User = Depends(require_app_permission("delete")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Revoke the project's direct user entry."""
    await _project(db, project_id, lock=True)
    entry = await _entry(db, project_id, membership_id)
    await record_audit_event(
        db,
        "project_member.removed",
        target_type="user",
        target_id=entry.user_id,
        project_id=project_id,
        details={
            "membership_id": entry.id,
            "policy_group_id": entry.policy_group_id,
            "owner": entry.owner,
            "policy_ids": sorted(policy.id for policy in entry.policies),
        },
    )
    await db.delete(entry)


@router.get("/{project_id}/permissions", response_model=dict[str, list[str]])
async def get_my_project_permissions(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Return the current user's effective permission operations for the project."""
    return as_lists(await effective_permissions(db, current_user, project_id))


class AccessOrigin(BaseModel):
    kind: str
    owner: bool = False
    inherit_policies: bool = False
    group: str | None = None
    policies: list[str]


class ProjectAccessEntry(BaseModel):
    user_id: int
    email: str
    full_name: str
    profile_picture_url: str | None = None
    origins: list[AccessOrigin]


@router.get(
    "/{project_id}/access",
    response_model=list[ProjectAccessEntry],
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def list_project_access(
    project_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Report direct and group entries from the same storage authorization reads."""
    await _project(db, project_id)
    return await project_access_entries(db, project_id)


async def project_access_entries(db: AsyncSession, project_id: int) -> list[ProjectAccessEntry]:
    """One entry per user with access to the project, with every origin of that access."""
    entries = {}
    rows = (
        (
            await db.execute(
                select(ProjectAccess)
                .where(ProjectAccess.project_id == project_id)
                .order_by(ProjectAccess.id)
            )
        )
        .scalars()
        .all()
    )
    replaced_users = {
        row.user_id for row in rows if row.user_id is not None and not row.inherit_policies
    }
    for row in rows:
        if row.user_id is not None:
            users = [await db.get(User, row.user_id)]
            group = None
        else:
            group = await db.get(Group, row.group_id)
            users = (
                (
                    await db.execute(
                        select(User)
                        .join(GroupMembership, GroupMembership.user_id == User.id)
                        .where(GroupMembership.group_id == row.group_id)
                    )
                )
                .scalars()
                .all()
            )
        for user in users:
            if row.user_id is None and user.id in replaced_users:
                continue
            entry = entries.setdefault(
                user.id,
                ProjectAccessEntry(
                    user_id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    profile_picture_url=user.profile_picture_url,
                    origins=[],
                ),
            )
            if row.inherit_policies and row.policy_group_id is None:
                inherited_groups = (
                    (
                        await db.execute(
                            select(Group)
                            .join(GroupMembership, GroupMembership.group_id == Group.id)
                            .where(GroupMembership.user_id == user.id)
                            .order_by(Group.name)
                        )
                    )
                    .scalars()
                    .all()
                )
                for source_group in inherited_groups:
                    source = AccessOrigin(
                        kind="group",
                        owner=False,
                        inherit_policies=True,
                        group=source_group.name,
                        policies=[
                            policy.name
                            for policy in sorted(
                                source_group.policies, key=lambda policy: policy.id
                            )
                        ],
                    )
                    if source not in entry.origins:
                        entry.origins.append(source)
                if not inherited_groups:
                    source = AccessOrigin(kind="direct", inherit_policies=True, policies=[])
                    if source not in entry.origins:
                        entry.origins.append(source)
                continue
            if row.policy_group_id:
                origin_group = row.policy_group.name
            else:
                origin_group = group.name if group else None
            entry.origins.append(
                AccessOrigin(
                    kind="direct" if row.user_id is not None else "group",
                    owner=row.owner,
                    inherit_policies=False,
                    group=origin_group,
                    policies=[
                        policy.name
                        for policy in sorted(
                            row.policy_group.policies if row.policy_group_id else row.policies,
                            key=lambda policy: policy.id,
                        )
                    ],
                )
            )
    return sorted(entries.values(), key=lambda entry: entry.full_name.lower())
