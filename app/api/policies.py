"""Administrator-managed resource policies with independent permissions and origins."""

import copy
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import (
    DOC_TYPE_RESOURCES,
    POLICY_RESOURCES,
    RESOURCE_ACTIONS,
    RESOURCES,
    actions_for_rule,
    actions_on,
    rule_of,
)
from app.core.security import require_app_permission
from app.models.groups import Policy, group_policies, user_application_policies
from app.models.project_membership import project_access_policies
from app.models.tags import Tag
from app.models.user import User
from app.schemas.groups import (
    PolicyCreate,
    PolicyResponse,
    PolicyRule,
    PolicyRuleResponse,
    PolicyUpdate,
)
from app.services.audit import record_audit_event

router = APIRouter()

require_admin = require_app_permission("view")


async def _get_policy_or_404(db: AsyncSession, policy_id: int) -> Policy:
    policy = await db.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


def policy_rules(policy: Policy) -> dict[str, PolicyRuleResponse]:
    """Return each rule's permission fields, origins and supported actions."""
    rules = {}
    for resource in POLICY_RESOURCES:
        actions = actions_on(policy.permissions, resource)
        if not actions:
            continue
        read, write, review, approve, delete = rule_of(actions)
        scope = (policy.type_tags or {}).get(resource) or {}
        rules[resource] = PolicyRuleResponse(
            read=read,
            write=write,
            review=review,
            approve=approve,
            delete=delete,
            all_origins=scope.get("all", False),
            visibility=scope.get("visibility") or [],
            tags=scope.get("tags") or [],
            actions=sorted(actions),
        )
    return rules


def _response(policy: Policy) -> PolicyResponse:
    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        scope=policy.scope,
        rules=policy_rules(policy),
        is_default=policy.is_default,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


async def _validate_rules(
    db: AsyncSession, rules: dict[str, PolicyRule], scope: str = "project"
) -> None:
    """Validate assignment scope, supported actions and document origin selections."""
    if scope == "document":
        allowed = DOC_TYPE_RESOURCES
    elif scope == "project":
        allowed = RESOURCES
    else:
        allowed = POLICY_RESOURCES
    unknown = sorted(set(rules) - set(allowed))
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown resources: {unknown}")
    tag_ids: set[int] = set()
    for resource, rule in rules.items():
        if rule.review and "review" not in RESOURCE_ACTIONS[resource]:
            raise HTTPException(status_code=400, detail=f"Review is not supported on {resource}.")
        if rule.approve and "approve" not in RESOURCE_ACTIONS[resource]:
            raise HTTPException(status_code=400, detail=f"Approve is not supported on {resource}.")
        if rule.delete and "delete" not in RESOURCE_ACTIONS[resource]:
            raise HTTPException(status_code=400, detail=f"Delete is not supported on {resource}.")
        if resource not in DOC_TYPE_RESOURCES:
            if rule.all_origins or rule.visibility or rule.tags:
                raise HTTPException(status_code=400, detail=f"{resource} takes no tags.")
            continue
        if (rule.read or rule.write or rule.review or rule.approve or rule.delete) and not (
            rule.all_origins or rule.visibility or rule.tags
        ):
            raise HTTPException(status_code=400, detail=f"Choose at least one tag for {resource}.")
        tag_ids.update(rule.tags)
    if tag_ids:
        known = set((await db.execute(select(Tag.id).where(Tag.id.in_(tag_ids)))).scalars().all())
        if tag_ids - known:
            raise HTTPException(status_code=400, detail=f"Unknown tags: {sorted(tag_ids - known)}")


def _apply_rules(policy: Policy, rules: dict[str, PolicyRule]) -> None:
    """Store permissions and origins while retaining unchanged operation selections."""
    permissions: dict = {}
    type_tags: dict = {}
    for resource, rule in rules.items():
        if not (rule.read or rule.write or rule.review or rule.approve or rule.delete):
            continue
        stored = actions_on(policy.permissions, resource)
        if stored and rule_of(stored) == (
            rule.read,
            rule.write,
            rule.review,
            rule.approve,
            rule.delete,
        ):
            permissions[resource] = sorted(stored)
        else:
            permissions[resource] = actions_for_rule(
                resource,
                rule.read,
                rule.write,
                rule.delete,
                review=rule.review,
                approve=rule.approve,
            )
        if resource in DOC_TYPE_RESOURCES:
            type_tags[resource] = {
                "all": rule.all_origins,
                "visibility": sorted(set(rule.visibility)),
                "tags": sorted(set(rule.tags)),
            }
    policy.permissions = permissions
    policy.type_tags = type_tags


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    _admin: User = Depends(require_app_permission("view")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    result = await db.execute(select(Policy).order_by(Policy.is_default.desc(), Policy.name.asc()))
    return [_response(p) for p in result.scalars().all()]


@router.post(
    "",
    response_model=PolicyResponse,
    status_code=201,
    responses={400: {"description": HTTPStatus(400).phrase}},
)
async def create_policy(
    data: PolicyCreate,
    _admin: User = Depends(require_app_permission("create")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    existing = await db.execute(select(Policy).where(Policy.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A policy with this name already exists")
    await _validate_rules(db, data.rules, data.scope)
    policy = Policy(
        name=data.name, description=data.description, scope=data.scope, is_default=False
    )
    _apply_rules(policy, data.rules)
    db.add(policy)
    await db.flush()
    await record_audit_event(
        db,
        "policy.created",
        target_type="policy",
        target_id=policy.id,
        details={"name": policy.name},
    )
    await db.refresh(policy)
    return _response(policy)


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def get_policy(
    policy_id: int,
    _admin: User = Depends(require_app_permission("view")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return _response(await _get_policy_or_404(db, policy_id))


@router.patch(
    "/{policy_id}",
    response_model=PolicyResponse,
    responses={
        400: {"description": HTTPStatus(400).phrase},
        403: {"description": HTTPStatus(403).phrase},
        404: {"description": HTTPStatus(404).phrase},
        409: {"description": HTTPStatus(409).phrase},
    },
)
async def update_policy(
    policy_id: int,
    data: PolicyUpdate,
    _admin: User = Depends(require_app_permission("edit")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    policy = await _get_policy_or_404(db, policy_id)
    if policy.is_default:
        raise HTTPException(
            status_code=403,
            detail="Default policies are read-only; duplicate one to change it.",
        )
    if data.name is not None and data.name != policy.name:
        clash = await db.scalar(
            select(Policy.id).where(Policy.name == data.name, Policy.id != policy.id)
        )
        if clash is not None:
            raise HTTPException(status_code=409, detail="A policy with this name already exists")
        policy.name = data.name
    if data.description is not None:
        policy.description = data.description
    scope = data.scope if data.scope is not None else policy.scope
    if scope != "app" and policy.scope == "app":
        assigned = await db.scalar(
            select(user_application_policies.c.user_id)
            .where(user_application_policies.c.policy_id == policy.id)
            .limit(1)
        )
        if assigned is not None:
            raise HTTPException(
                status_code=409,
                detail="An assigned application policy cannot become a project or document policy",
            )
    if scope == "app" and policy.scope != "app":
        assigned = await db.scalar(
            select(project_access_policies.c.access_id)
            .where(project_access_policies.c.policy_id == policy.id)
            .limit(1)
        )
        if assigned is not None:
            raise HTTPException(
                status_code=409,
                detail="A policy assigned on a project cannot become an application policy",
            )
    if data.rules is not None:
        await _validate_rules(db, data.rules, scope)
        _apply_rules(policy, data.rules)
    elif data.scope is not None:
        await _validate_rules(db, policy_rules(policy), scope)
    policy.scope = scope
    await record_audit_event(
        db,
        "policy.updated",
        target_type="policy",
        target_id=policy.id,
        details={"name": policy.name, "fields": sorted(data.model_fields_set)},
    )
    await db.refresh(policy)
    return _response(policy)


@router.post(
    "/{policy_id}/duplicate",
    response_model=PolicyResponse,
    status_code=201,
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def duplicate_policy(
    policy_id: int,
    _admin: User = Depends(require_app_permission("create")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    """Create an editable copy of the policy under the first free "(copy)" name."""
    source = await _get_policy_or_404(db, policy_id)
    taken = set((await db.execute(select(Policy.name))).scalars().all())
    stem = source.name[:70]
    name, number = f"{stem} (copy)", 2
    while name in taken:
        name, number = f"{stem} (copy {number})", number + 1
    policy = Policy(
        name=name,
        description=source.description,
        scope=source.scope,
        permissions=copy.deepcopy(source.permissions or {}),
        type_tags=copy.deepcopy(source.type_tags or {}),
        is_default=False,
    )
    db.add(policy)
    await db.flush()
    await record_audit_event(
        db,
        "policy.created",
        target_type="policy",
        target_id=policy.id,
        details={"name": policy.name, "duplicated_from": source.id},
    )
    await db.refresh(policy)
    return _response(policy)


@router.delete(
    "/{policy_id}",
    status_code=204,
    responses={
        400: {"description": HTTPStatus(400).phrase},
        404: {"description": HTTPStatus(404).phrase},
        409: {"description": HTTPStatus(409).phrase},
    },
)
async def delete_policy(
    policy_id: int,
    _admin: User = Depends(require_app_permission("delete")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    policy = await _get_policy_or_404(db, policy_id)
    if policy.is_default:
        raise HTTPException(status_code=400, detail="Default policies cannot be deleted")
    in_use = await db.scalar(
        select(func.count())
        .select_from(project_access_policies)
        .where(project_access_policies.c.policy_id == policy_id)
    )
    in_group = await db.scalar(
        select(func.count())
        .select_from(group_policies)
        .where(group_policies.c.policy_id == policy_id)
    )
    in_app = await db.scalar(
        select(func.count())
        .select_from(user_application_policies)
        .where(user_application_policies.c.policy_id == policy_id)
    )
    if in_use or in_group or in_app:
        raise HTTPException(
            status_code=409,
            detail="Policy is assigned to a group or project access and cannot be deleted",
        )
    await db.delete(policy)
    await record_audit_event(
        db,
        "policy.deleted",
        target_type="policy",
        target_id=policy_id,
        details={"name": policy.name},
    )
