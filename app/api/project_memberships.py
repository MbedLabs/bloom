"""
Project membership management (admin only).

Endpoints:
    GET    /api/projects/{project_id}/members          — list all members
    POST   /api/projects/{project_id}/members          — add a member
    GET    /api/projects/{project_id}/members/{id}     — get one membership
    PATCH  /api/projects/{project_id}/members/{id}     — update role / doc_types
    DELETE /api/projects/{project_id}/members/{id}     — remove a member
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_project_role
from app.models.project_membership import ProjectExternalDocType, ProjectMembership
from app.models.user import User, UserRole
from app.schemas.memberships import (
    DEFAULT_EXTERNAL_DOC_TYPES,
    EXTERNAL_DOC_TYPES,
    ProjectMemberResponse,
    ProjectMembershipCreate,
    ProjectMembershipUpdate,
)

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
    _admin: User = Depends(require_project_role("admin")),
    db: AsyncSession = Depends(get_db),
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
    _admin: User = Depends(require_project_role("admin")),
    db: AsyncSession = Depends(get_db),
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

    await db.refresh(membership)
    return await _build_member_response(db, membership)


@router.get("/{project_id}/members/{membership_id}", response_model=ProjectMemberResponse)
async def get_project_member(
    project_id: int,
    membership_id: int,
    _admin: User = Depends(require_project_role("admin")),
    db: AsyncSession = Depends(get_db),
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
    _admin: User = Depends(require_project_role("admin")),
    db: AsyncSession = Depends(get_db),
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

    if data.role is not None:
        membership.role = data.role
        await db.flush()

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

    await db.refresh(membership)
    return await _build_member_response(db, membership)


@router.delete("/{project_id}/members/{membership_id}", status_code=204)
async def remove_project_member(
    project_id: int,
    membership_id: int,
    _admin: User = Depends(require_project_role("admin")),
    db: AsyncSession = Depends(get_db),
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
