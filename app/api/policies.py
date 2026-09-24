"""Policies API (admin only): the named permission sets that groups carry.

The shipped default policies are protected: they cannot be deleted
and their base_role is fixed, since group project access relies on it. Their
description, permissions and doc-tag scope stay editable so an operator can tune a
default policy in place.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import invalid_entries
from app.core.security import require_role
from app.models.groups import Group, Policy
from app.models.user import User, UserRole
from app.schemas.groups import PolicyCreate, PolicyResponse, PolicyUpdate
from app.schemas.memberships import EXTERNAL_DOC_TYPES
from app.services.audit import record_audit_event

router = APIRouter()

require_admin = require_role(UserRole.admin)


async def _get_policy_or_404(db: AsyncSession, policy_id: int) -> Policy:
    policy = await db.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


def _validate_doc_tag_scope(doc_tag_scope) -> None:
    """doc_tag_scope is the external document-type allowlist, so its entries must be
    known document-type codes."""
    if doc_tag_scope is None:
        return
    invalid = set(doc_tag_scope) - EXTERNAL_DOC_TYPES
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown document types {sorted(invalid)}. Allowed: {sorted(EXTERNAL_DOC_TYPES)}",
        )


def _validate_permissions(permissions: dict) -> None:
    """A policy matrix may only name the resources and actions require_permission checks."""
    problems = invalid_entries(permissions)
    if problems:
        raise HTTPException(status_code=400, detail="Invalid permissions: " + "; ".join(problems))


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(select(Policy).order_by(Policy.is_default.desc(), Policy.name.asc()))
    return [PolicyResponse.model_validate(p) for p in result.scalars().all()]


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    data: PolicyCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    existing = await db.execute(select(Policy).where(Policy.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A policy with this name already exists")
    _validate_doc_tag_scope(data.doc_tag_scope)
    _validate_permissions(data.permissions)
    policy = Policy(
        name=data.name,
        description=data.description,
        base_role=data.base_role,
        permissions=data.permissions,
        doc_tag_scope=data.doc_tag_scope,
        is_default=False,
    )
    db.add(policy)
    await db.flush()
    await record_audit_event(
        db,
        "policy.created",
        target_type="policy",
        target_id=policy.id,
        details={"name": policy.name, "base_role": policy.base_role},
    )
    await db.refresh(policy)
    return PolicyResponse.model_validate(policy)


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return PolicyResponse.model_validate(await _get_policy_or_404(db, policy_id))


@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: int,
    data: PolicyUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    policy = await _get_policy_or_404(db, policy_id)
    if data.description is not None:
        policy.description = data.description
    if data.permissions is not None:
        _validate_permissions(data.permissions)
        policy.permissions = data.permissions
    if "doc_tag_scope" in data.model_fields_set:
        _validate_doc_tag_scope(data.doc_tag_scope)
        policy.doc_tag_scope = data.doc_tag_scope
    if data.base_role is not None and data.base_role != policy.base_role:
        if policy.is_default:
            raise HTTPException(
                status_code=400,
                detail="A default policy's base role cannot be changed",
            )
        policy.base_role = data.base_role
    await record_audit_event(
        db,
        "policy.updated",
        target_type="policy",
        target_id=policy.id,
        details={"name": policy.name, "fields": sorted(data.model_fields_set)},
    )
    await db.refresh(policy)
    return PolicyResponse.model_validate(policy)


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    policy = await _get_policy_or_404(db, policy_id)
    if policy.is_default:
        raise HTTPException(status_code=400, detail="Default policies cannot be deleted")
    in_use = await db.scalar(
        select(func.count()).select_from(Group).where(Group.policy_id == policy_id)
    )
    if in_use:
        raise HTTPException(
            status_code=409,
            detail="Policy is assigned to one or more groups and cannot be deleted",
        )
    await db.delete(policy)
    await record_audit_event(
        db,
        "policy.deleted",
        target_type="policy",
        target_id=policy_id,
        details={"name": policy.name},
    )
