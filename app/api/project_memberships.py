"""Project membership management, and who has access to a project and why."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import as_lists
from app.core.security import (
    effective_permissions,
    get_current_user,
    require_permission,
)
from app.models.groups import Group, GroupMembership, GroupProjectGrant, Policy
from app.models.project_membership import ProjectExternalDocType, ProjectMembership
from app.models.user import User, UserRole
from app.schemas.memberships import (
    DEFAULT_EXTERNAL_DOC_TYPES,
    EXTERNAL_DOC_TYPES,
    ProjectMemberResponse,
    ProjectMembershipCreate,
    ProjectMembershipUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter()


async def _build_member_response(
    db: AsyncSession, membership: ProjectMembership
) -> ProjectMemberResponse:
    user_row = await db.execute(select(User).where(User.id == membership.user_id))
    user = user_row.scalar_one_or_none()

    doc_types: list[str] = []
    if membership.role == "external":
        result = await db.execute(
            select(ProjectExternalDocType.doc_type).where(
                ProjectExternalDocType.membership_id == membership.id
            )
        )
        doc_types = sorted(result.scalars().all())

    return ProjectMemberResponse(
        id=membership.id,
        user_id=membership.user_id,
        email=user.email if user else "",
        full_name=user.full_name if user else "",
        role=membership.role,
        doc_types=doc_types,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
async def list_project_members(
    project_id: int,
    _allowed: User = Depends(require_permission("view", "member")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(
        select(ProjectMembership).where(ProjectMembership.project_id == project_id)
    )
    memberships = result.scalars().all()
    return [await _build_member_response(db, m) for m in memberships]


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=201)
async def add_project_member(
    project_id: int,
    data: ProjectMembershipCreate,
    _allowed: User = Depends(require_permission("manage", "member")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    user_row = await db.execute(select(User).where(User.id == data.user_id))
    user = user_row.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Admin users do not need project memberships")

    existing = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.user_id == data.user_id,
            ProjectMembership.project_id == project_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member of this project")

    doc_types = data.doc_types
    if data.role == "external":
        if doc_types is None:
            doc_types = list(DEFAULT_EXTERNAL_DOC_TYPES)
        invalid = set(doc_types) - EXTERNAL_DOC_TYPES
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid doc types: {sorted(invalid)}. "
                f"Allowed: {sorted(EXTERNAL_DOC_TYPES)}",
            )

    membership = ProjectMembership(
        user_id=data.user_id,
        project_id=project_id,
        role=data.role,
    )
    db.add(membership)
    await db.flush()

    if data.role == "external" and doc_types:
        for dt in sorted(doc_types):
            db.add(ProjectExternalDocType(membership_id=membership.id, doc_type=dt))
        await db.flush()

    await record_audit_event(
        db,
        "project_member.added",
        target_type="user",
        target_id=membership.user_id,
        project_id=project_id,
        details={
            "role": membership.role,
            "doc_types": sorted(doc_types) if data.role == "external" and doc_types else [],
        },
    )
    await db.refresh(membership)
    return await _build_member_response(db, membership)


@router.get("/{project_id}/members/{membership_id}", response_model=ProjectMemberResponse)
async def get_project_member(
    project_id: int,
    membership_id: int,
    _allowed: User = Depends(require_permission("view", "member")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.id == membership_id,
            ProjectMembership.project_id == project_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    return await _build_member_response(db, membership)


@router.patch("/{project_id}/members/{membership_id}", response_model=ProjectMemberResponse)
async def update_project_member(
    project_id: int,
    membership_id: int,
    data: ProjectMembershipUpdate,
    _allowed: User = Depends(require_permission("manage", "member")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.id == membership_id,
            ProjectMembership.project_id == project_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    previous_role = membership.role
    if data.role is not None:
        membership.role = data.role
        await db.flush()
    if membership.role != previous_role:
        await record_audit_event(
            db,
            "project_member.role_changed",
            target_type="user",
            target_id=membership.user_id,
            project_id=project_id,
            details={"from": previous_role, "to": membership.role},
        )

    if data.doc_types is not None:
        await db.execute(
            delete(ProjectExternalDocType).where(
                ProjectExternalDocType.membership_id == membership.id
            )
        )
        if membership.role == "external":
            invalid = set(data.doc_types) - EXTERNAL_DOC_TYPES
            if invalid:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid doc types: {sorted(invalid)}. "
                    f"Allowed: {sorted(EXTERNAL_DOC_TYPES)}",
                )
            for dt in sorted(data.doc_types):
                db.add(ProjectExternalDocType(membership_id=membership.id, doc_type=dt))
        await db.flush()
        await record_audit_event(
            db,
            "project_member.doc_types_changed",
            target_type="user",
            target_id=membership.user_id,
            project_id=project_id,
            details={"doc_types": sorted(data.doc_types) if membership.role == "external" else []},
        )

    await db.refresh(membership)
    return await _build_member_response(db, membership)


@router.delete("/{project_id}/members/{membership_id}", status_code=204)
async def remove_project_member(
    project_id: int,
    membership_id: int,
    _allowed: User = Depends(require_permission("manage", "member")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.id == membership_id,
            ProjectMembership.project_id == project_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    await db.delete(membership)
    await record_audit_event(
        db,
        "project_member.removed",
        target_type="user",
        target_id=membership.user_id,
        project_id=project_id,
        details={"role": membership.role},
    )


@router.get("/{project_id}/permissions", response_model=dict[str, list[str]])
async def get_my_project_permissions(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """The current user's effective permissions on the project, as {resource: [action]}.

    ``*`` stands for every resource or every action. An empty object means no access.
    """
    return as_lists(await effective_permissions(db, current_user, project_id))


class AccessOrigin(BaseModel):
    kind: str
    role: str | None = None
    group: str | None = None
    policy: str | None = None
    all_projects: bool = False


class ProjectAccessEntry(BaseModel):
    user_id: int
    email: str
    full_name: str
    origins: list[AccessOrigin]


@router.get("/{project_id}/access", response_model=list[ProjectAccessEntry])
async def list_project_access(
    project_id: int,
    _allowed: User = Depends(require_permission("view", "member")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Everyone with access to the project and why: a direct membership with its role,
    and every group granted the project (or all projects) with its policy."""
    entries: dict[int, ProjectAccessEntry] = {}

    def entry_for(user: User) -> ProjectAccessEntry:
        if user.id not in entries:
            entries[user.id] = ProjectAccessEntry(
                user_id=user.id, email=user.email, full_name=user.full_name, origins=[]
            )
        return entries[user.id]

    direct = await db.execute(
        select(User, ProjectMembership.role)
        .join(ProjectMembership, ProjectMembership.user_id == User.id)
        .where(ProjectMembership.project_id == project_id)
    )
    for user, role in direct.all():
        entry_for(user).origins.append(AccessOrigin(kind="direct", role=role))

    via_groups = await db.execute(
        select(User, Group.name, Policy.name, GroupProjectGrant.project_id)
        .select_from(GroupMembership)
        .join(User, User.id == GroupMembership.user_id)
        .join(Group, Group.id == GroupMembership.group_id)
        .join(GroupProjectGrant, GroupProjectGrant.group_id == Group.id)
        .outerjoin(Policy, Policy.id == Group.policy_id)
        .where(
            (GroupProjectGrant.project_id == project_id) | (GroupProjectGrant.project_id.is_(None))
        )
        .order_by(Group.name)
    )
    for user, group_name, policy_name, granted_project in via_groups.all():
        entry_for(user).origins.append(
            AccessOrigin(
                kind="group",
                group=group_name,
                policy=policy_name,
                all_projects=granted_project is None,
            )
        )
    return sorted(entries.values(), key=lambda e: e.full_name.lower())
