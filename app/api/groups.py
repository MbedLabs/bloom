"""Administrator-managed group policy sets, memberships and project admission."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import require_app_permission, require_role
from app.models import Project
from app.models.groups import Group, GroupMembership, Policy
from app.models.project_membership import ProjectAccess
from app.models.user import User, UserRole
from app.schemas.groups import (
    GroupAssignmentCreate,
    GroupCreate,
    GroupGrantCreate,
    GroupGrantResponse,
    GroupGrantUpdate,
    GroupMemberCreate,
    GroupMemberResponse,
    GroupMembersCreate,
    GroupResponse,
    GroupUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter()

require_admin = require_role(UserRole.admin)


async def _get_group_or_404(db: AsyncSession, group_id: int) -> Group:
    group = await db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


async def _group_response(db: AsyncSession, group: Group) -> GroupResponse:
    """Serialise a group with its members (joined to their users) and grants.

    Relationships are read with explicit queries rather than lazy attribute
    access, which the async session does not allow.
    """
    member_rows = (
        await db.execute(
            select(GroupMembership.user_id, User.email, User.full_name)
            .join(User, User.id == GroupMembership.user_id)
            .where(GroupMembership.group_id == group.id)
            .order_by(User.full_name.asc())
        )
    ).all()
    grant_rows = (
        (
            await db.execute(
                select(ProjectAccess)
                .options(selectinload(ProjectAccess.policies))
                .where(ProjectAccess.group_id == group.id)
                .order_by(ProjectAccess.id.asc())
            )
        )
        .scalars()
        .all()
    )
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        policy_ids=sorted(policy.id for policy in group.policies),
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=[
            GroupMemberResponse(user_id=r.user_id, email=r.email, full_name=r.full_name)
            for r in member_rows
        ],
        grants=[
            GroupGrantResponse(
                id=g.id,
                project_id=g.project_id,
            )
            for g in grant_rows
        ],
    )


async def _selected_policies(db: AsyncSession, policy_ids: list[int]) -> list[Policy]:
    """Resolve every selected policy or reject the whole assignment."""
    policies = (
        (await db.execute(select(Policy).where(Policy.id.in_(policy_ids)).order_by(Policy.id)))
        .scalars()
        .all()
    )
    if len(policies) != len(policy_ids):
        raise HTTPException(status_code=404, detail="Policy not found")
    return list(policies)


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    _admin: User = Depends(require_app_permission("view")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    groups = (await db.execute(select(Group).order_by(Group.name.asc()))).scalars().all()
    return [await _group_response(db, group) for group in groups]


@router.get("/assignment-options")
async def assignment_options(
    _manager: User = Depends(require_app_permission("view")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """List minimal project and user choices for access assignment."""
    projects = (
        await db.execute(select(Project.id, Project.name, Project.prefix).order_by(Project.name))
    ).all()
    users = (
        (await db.execute(select(User).where(User.is_active.is_(True)).order_by(User.full_name)))
        .scalars()
        .all()
    )
    return {
        "projects": [dict(row._mapping) for row in projects],
        "users": [
            {
                "id": row.id,
                "full_name": row.full_name,
                "profile_picture_url": row.profile_picture_url,
                "email": row.email,
                "role": row.role.value if hasattr(row.role, "value") else str(row.role),
            }
            for row in users
        ],
    }


@router.post("/{group_id}/assignments")
async def assign_project_bundle(
    group_id: int,
    data: GroupAssignmentCreate,
    _manager: User = Depends(require_app_permission("edit")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Assign the bundle to selected users only on the addressed project."""
    from app.api.project_memberships import _response

    group = await _get_group_or_404(db, group_id)
    if not group.policies:
        raise HTTPException(status_code=400, detail="Choose a group with policies")
    if await db.get(Project, data.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    users = list(await db.scalars(select(User).where(User.id.in_(data.user_ids))))
    if len(users) != len(data.user_ids):
        raise HTTPException(status_code=404, detail="User not found")
    if any(not user.is_active for user in users):
        raise HTTPException(status_code=400, detail="Choose active users")
    rows = list(
        await db.scalars(
            select(ProjectAccess).where(
                ProjectAccess.project_id == data.project_id,
                ProjectAccess.user_id.in_(data.user_ids),
            )
        )
    )
    known = {row.user_id: row for row in rows}
    result = []
    for user_id in data.user_ids:
        row = known.get(user_id)
        if row is None:
            row = ProjectAccess(project_id=data.project_id, user_id=user_id, policies=[])
            db.add(row)
        row.owner = False
        row.inherit_policies = False
        row.policies = []
        row.policy_group_id = group.id
        row.policy_group = group
        await db.flush()
        await record_audit_event(
            db,
            "project_member.bundle_assigned",
            target_type="user",
            target_id=user_id,
            project_id=data.project_id,
            details={"policy_group_id": group.id},
        )
        result.append(await _response(db, row))
    return result


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    data: GroupCreate,
    _admin: User = Depends(require_app_permission("create")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    if (await db.execute(select(Group).where(Group.name == data.name))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A group with this name already exists")
    group = Group(
        name=data.name,
        description=data.description,
        policies=await _selected_policies(db, data.policy_ids),
    )
    db.add(group)
    await db.flush()
    await record_audit_event(
        db,
        "group.created",
        target_type="group",
        target_id=group.id,
        details={"name": group.name},
    )
    await db.refresh(group)
    return await _group_response(db, group)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int,
    _admin: User = Depends(require_app_permission("view")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _group_response(db, await _get_group_or_404(db, group_id))


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    data: GroupUpdate,
    _admin: User = Depends(require_app_permission("edit")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    group = await _get_group_or_404(db, group_id)
    if data.name is not None and data.name != group.name:
        clash = (
            await db.execute(select(Group).where(Group.name == data.name, Group.id != group_id))
        ).scalar_one_or_none()
        if clash:
            raise HTTPException(status_code=400, detail="A group with this name already exists")
        group.name = data.name
    if data.description is not None:
        group.description = data.description
    if data.policy_ids is not None:
        group.policies = await _selected_policies(db, data.policy_ids)
    await record_audit_event(
        db,
        "group.updated",
        target_type="group",
        target_id=group.id,
        details={"fields": sorted(data.model_fields_set)},
    )
    await db.refresh(group)
    return await _group_response(db, group)


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: int,
    _admin: User = Depends(require_app_permission("delete")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    group = await _get_group_or_404(db, group_id)
    if (
        await db.scalar(
            select(ProjectAccess.id).where(ProjectAccess.policy_group_id == group_id).limit(1)
        )
        is not None
    ):
        raise HTTPException(status_code=409, detail="Group is assigned to a project user")
    await record_audit_event(
        db, "group.deleted", target_type="group", target_id=group_id, details={"name": group.name}
    )
    access_rows = (
        (await db.execute(select(ProjectAccess).where(ProjectAccess.group_id == group_id)))
        .scalars()
        .all()
    )
    for access in access_rows:
        await db.delete(access)
    await db.flush()
    await db.execute(delete(GroupMembership).where(GroupMembership.group_id == group_id))
    await db.execute(delete(Group).where(Group.id == group_id))
    await db.flush()


@router.post("/{group_id}/members", response_model=GroupResponse, status_code=201)
async def add_member(
    group_id: int,
    data: GroupMemberCreate | GroupMembersCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    group = await _get_group_or_404(db, group_id)
    bulk = isinstance(data, GroupMembersCreate)
    requested = data.user_ids if bulk else [data.user_id]
    found = set((await db.scalars(select(User.id).where(User.id.in_(requested)))).all())
    if found != set(requested):
        raise HTTPException(status_code=404, detail="User not found")
    existing = set(
        (
            await db.scalars(
                select(GroupMembership.user_id).where(
                    GroupMembership.group_id == group_id,
                    GroupMembership.user_id.in_(requested),
                )
            )
        ).all()
    )
    if existing and not bulk:
        raise HTTPException(status_code=409, detail="User is already a member of this group")
    for user_id in requested:
        if user_id not in existing:
            db.add(GroupMembership(group_id=group_id, user_id=user_id))
            await record_audit_event(
                db,
                "group.member_added",
                target_type="group",
                target_id=group_id,
                actor_user_id=_admin.id,
                details={"user_id": user_id},
            )
    return await _group_response(db, group)


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_member(
    group_id: int,
    user_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    await _get_group_or_404(db, group_id)
    row = (
        await db.execute(
            select(GroupMembership).where(
                GroupMembership.group_id == group_id,
                GroupMembership.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    await db.delete(row)
    await record_audit_event(
        db,
        "group.member_removed",
        target_type="group",
        target_id=group_id,
        details={"user_id": user_id},
    )


@router.post("/{group_id}/grants", response_model=GroupResponse, status_code=201)
async def add_grant(
    group_id: int,
    data: GroupGrantCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    group = await _get_group_or_404(db, group_id)
    if await db.get(Project, data.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = await db.scalar(
        select(ProjectAccess.id).where(
            ProjectAccess.group_id == group_id, ProjectAccess.project_id == data.project_id
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Group already has this project assignment")
    db.add(
        ProjectAccess(
            group_id=group_id, project_id=data.project_id, inherit_policies=True, policies=[]
        )
    )
    await db.flush()
    await record_audit_event(
        db,
        "group.grant_added",
        target_type="group",
        target_id=group_id,
        project_id=data.project_id,
        details={"inherit_policies": True},
    )
    return await _group_response(db, group)


@router.patch("/{group_id}/grants/{grant_id}", response_model=GroupResponse)
async def update_grant(
    group_id: int,
    grant_id: int,
    data: GroupGrantUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Keep group admission separate from the group's policy definition."""
    group = await _get_group_or_404(db, group_id)
    row = await db.scalar(
        select(ProjectAccess).where(
            ProjectAccess.id == grant_id, ProjectAccess.group_id == group_id
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Grant not found")
    row.inherit_policies = True
    row.policies = []
    await db.flush()
    await record_audit_event(
        db,
        "group.grant_updated",
        target_type="group",
        target_id=group_id,
        project_id=row.project_id,
        details={"inherit_policies": True},
    )
    return await _group_response(db, group)


@router.delete("/{group_id}/grants/{grant_id}", status_code=204)
async def remove_grant(
    group_id: int,
    grant_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    await _get_group_or_404(db, group_id)
    row = (
        await db.execute(
            select(ProjectAccess).where(
                ProjectAccess.id == grant_id,
                ProjectAccess.group_id == group_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Grant not found")
    await db.delete(row)
    await record_audit_event(
        db,
        "group.grant_removed",
        target_type="group",
        target_id=group_id,
        project_id=row.project_id,
        details={"policy_ids": sorted(policy.id for policy in row.policies)},
    )
