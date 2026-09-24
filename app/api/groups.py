"""Groups API (admin only): named sets of users that carry a policy and are
granted projects.

A group grant adds project access on top of a user's direct memberships; it never
removes any. The effective role resolution lives in
app.core.security.require_project_access, so a user in no group behaves exactly as
their role does today.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.models import Project
from app.models.groups import Group, GroupMembership, GroupProjectGrant, Policy
from app.models.user import User, UserRole
from app.schemas.groups import (
    GroupCreate,
    GroupGrantCreate,
    GroupGrantResponse,
    GroupMemberCreate,
    GroupMemberResponse,
    GroupResponse,
    GroupUpdate,
)

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
                select(GroupProjectGrant)
                .where(GroupProjectGrant.group_id == group.id)
                .order_by(GroupProjectGrant.id.asc())
            )
        )
        .scalars()
        .all()
    )
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        policy_id=group.policy_id,
        created_at=group.created_at,
        updated_at=group.updated_at,
        members=[
            GroupMemberResponse(user_id=r.user_id, email=r.email, full_name=r.full_name)
            for r in member_rows
        ],
        grants=[GroupGrantResponse(id=g.id, project_id=g.project_id) for g in grant_rows],
    )


async def _policy_exists_or_400(db: AsyncSession, policy_id: int) -> None:
    if await db.get(Policy, policy_id) is None:
        raise HTTPException(status_code=400, detail="Policy not found")


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    groups = (await db.execute(select(Group).order_by(Group.name.asc()))).scalars().all()
    return [await _group_response(db, group) for group in groups]


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    data: GroupCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    if (await db.execute(select(Group).where(Group.name == data.name))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A group with this name already exists")
    if data.policy_id is not None:
        await _policy_exists_or_400(db, data.policy_id)
    group = Group(name=data.name, description=data.description, policy_id=data.policy_id)
    db.add(group)
    await db.flush()
    await db.refresh(group)
    return await _group_response(db, group)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await _group_response(db, await _get_group_or_404(db, group_id))


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    data: GroupUpdate,
    _admin: User = Depends(require_admin),
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
    if "policy_id" in data.model_fields_set:
        if data.policy_id is not None:
            await _policy_exists_or_400(db, data.policy_id)
        group.policy_id = data.policy_id
    await db.flush()
    await db.refresh(group)
    return await _group_response(db, group)


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    await _get_group_or_404(db, group_id)
    await db.execute(delete(GroupMembership).where(GroupMembership.group_id == group_id))
    await db.execute(delete(GroupProjectGrant).where(GroupProjectGrant.group_id == group_id))
    await db.execute(delete(Group).where(Group.id == group_id))
    await db.flush()


@router.post("/{group_id}/members", response_model=GroupResponse, status_code=201)
async def add_member(
    group_id: int,
    data: GroupMemberCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    group = await _get_group_or_404(db, group_id)
    if await db.get(User, data.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    existing = (
        await db.execute(
            select(GroupMembership).where(
                GroupMembership.group_id == group_id,
                GroupMembership.user_id == data.user_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member of this group")
    db.add(GroupMembership(group_id=group_id, user_id=data.user_id))
    await db.flush()
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
    await db.flush()


@router.post("/{group_id}/grants", response_model=GroupResponse, status_code=201)
async def add_grant(
    group_id: int,
    data: GroupGrantCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    group = await _get_group_or_404(db, group_id)
    if data.project_id is not None and await db.get(Project, data.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if data.project_id is None:
        clause = and_(
            GroupProjectGrant.group_id == group_id,
            GroupProjectGrant.project_id.is_(None),
        )
    else:
        clause = and_(
            GroupProjectGrant.group_id == group_id,
            GroupProjectGrant.project_id == data.project_id,
        )
    if (await db.execute(select(GroupProjectGrant).where(clause))).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Group already has this grant")
    db.add(GroupProjectGrant(group_id=group_id, project_id=data.project_id))
    await db.flush()
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
            select(GroupProjectGrant).where(
                GroupProjectGrant.id == grant_id,
                GroupProjectGrant.group_id == group_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Grant not found")
    await db.delete(row)
    await db.flush()
