"""
Security utilities: password hashing, JWT token creation/verification, auth dependencies.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy import and_, false, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.document_kinds import CANONICAL_DOCUMENT_KINDS
from app.core.permissions import (
    ANY,
    APP_RESOURCES,
    DOC_TYPE_RESOURCES,
    EXTERNAL_DENIED_ACTIONS,
    RESOURCE_ACTIONS,
    RESOURCES,
    Permissions,
    actions_on,
    as_lists,
    has_permission,
    merge,
    role_baseline,
)
from app.models import ArtefactVisibility, Project
from app.models.groups import Group, GroupMembership, Policy, user_application_policies
from app.models.project_membership import ProjectAccess
from app.models.tags import TAG_TYPE_OF_MODEL, TYPE_CODES, ArtefactTag
from app.models.user import User, UserRole
from app.services.audit import set_audit_actor

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc).replace(tzinfo=None) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> User:
    """Return the active user of the bearer token. A token minted before the user's session_version
    changed (password change or reset, confirmed email change) is rejected.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "user":
            raise credentials_exception
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        entity_id = int(user_id)
    except (jwt.PyJWTError, TypeError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == entity_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    if payload.get("ver") != user.session_version:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )
    set_audit_actor("user", user.id)
    user.access_map = await _access_map(db, user)
    user.application_permissions = as_lists(await effective_permissions(db, user, None))
    return user


def require_role(*roles: UserRole):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' not authorized. Required: {[r.value for r in roles]}",
            )
        return current_user

    return role_checker


@dataclass(frozen=True)
class AccessTerm:
    """What one policy rule, or the Owner role, lets a user do and see on a project: the
    permission matrix, the document types it covers (None for all), the visibility tags it
    covers (None for every artefact), the further tags it covers and whether it covers
    customer artefacts only."""

    permissions: Permissions
    doc_types: Optional[frozenset]
    visibilities: Optional[frozenset]
    tags: frozenset
    customer_only: bool


def _policy_terms(policy, external: bool, resources=RESOURCES) -> list[AccessTerm]:
    """One term per resource the policy grants actions on, covering the tags the policy
    ticks for that resource; a document type with no tag ticked gives none. An external
    user's terms cover customer artefacts only and grant neither approve nor delete."""
    terms = []
    for resource in resources:
        actions = actions_on(policy.permissions, resource)
        if external:
            actions -= EXTERNAL_DENIED_ACTIONS
        if not actions:
            continue
        if resource in DOC_TYPE_RESOURCES:
            scope = (policy.type_tags or {}).get(resource) or {}
            if not (scope.get("all") or scope.get("visibility") or scope.get("tags")):
                continue
            terms.append(
                AccessTerm(
                    {resource: actions},
                    frozenset({resource}),
                    None if scope.get("all") else frozenset(scope.get("visibility") or []),
                    frozenset(scope.get("tags") or []),
                    external,
                )
            )
        else:
            terms.append(AccessTerm({resource: actions}, frozenset(), None, frozenset(), external))
    return terms


def _owner_term(external: bool) -> AccessTerm:
    """The Owner role's term: every action on every resource; for an external user every
    action but review, approve and delete, on customer artefacts only."""
    if not external:
        return AccessTerm({ANY: {ANY}}, None, None, frozenset(), False)
    return AccessTerm(
        {
            resource: set(RESOURCE_ACTIONS[resource] - EXTERNAL_DENIED_ACTIONS - {"review"})
            for resource in RESOURCES
        },
        None,
        None,
        frozenset(),
        True,
    )


async def _access_map(db: AsyncSession, user: User) -> dict:
    """For every project the user reaches through their own access entry or a group's,
    the terms that apply there; empty for an administrator, who holds everything.
    Terms covering the same tags are merged, their document types joined."""
    if user.role == UserRole.admin:
        return {}
    external = user.role == UserRole.external
    group_ids = select(GroupMembership.group_id).where(GroupMembership.user_id == user.id)
    entries = (
        (
            await db.execute(
                select(ProjectAccess).where(
                    or_(ProjectAccess.user_id == user.id, ProjectAccess.group_id.in_(group_ids))
                )
            )
        )
        .scalars()
        .all()
    )
    groups = (await db.execute(select(Group).where(Group.id.in_(group_ids)))).scalars().all()
    inherited = {policy.id: policy for group in groups for policy in group.policies}
    direct = {entry.project_id: entry for entry in entries if entry.user_id == user.id}
    by_project: dict = {}
    for entry in entries:
        override = direct.get(entry.project_id)
        if override is not None and not override.inherit_policies and entry is not override:
            continue
        merged = by_project.setdefault(entry.project_id, {})
        terms = [_owner_term(external)] if entry.owner else []
        selected = (
            entry.policy_group.policies
            if entry.policy_group_id is not None
            else inherited.values() if entry.inherit_policies else entry.policies
        )
        for policy in selected:
            terms.extend(_policy_terms(policy, external))
        for term in terms:
            key = (term.doc_types is None, term.visibilities, term.tags, term.customer_only)
            known = merged.get(key)
            merged[key] = AccessTerm(
                merge(merge({}, known.permissions if known else {}), term.permissions),
                (
                    None
                    if term.doc_types is None
                    else term.doc_types | (known.doc_types if known else frozenset())
                ),
                term.visibilities,
                term.tags,
                term.customer_only,
            )
    return {project_id: tuple(terms.values()) for project_id, terms in by_project.items()}


async def access_terms(db: AsyncSession, user: User, project_id: Optional[int]) -> tuple:
    """Configured app terms for no project, or content terms of an admitted project."""
    if project_id is None:
        group_ids = select(GroupMembership.group_id).where(GroupMembership.user_id == user.id)
        groups = (await db.execute(select(Group).where(Group.id.in_(group_ids)))).scalars().all()
        policies = {
            policy.id: policy
            for group in groups
            for policy in group.policies
            if policy.scope == "app"
        }
        assigned = await db.scalars(
            select(Policy)
            .join(user_application_policies)
            .where(user_application_policies.c.user_id == user.id, Policy.scope == "app")
        )
        policies.update({policy.id: policy for policy in assigned})
        return tuple(
            term
            for policy in policies.values()
            for term in _policy_terms(policy, user.role == UserRole.external, APP_RESOURCES)
        )
    access_map = getattr(user, "access_map", None)
    if access_map is None:
        access_map = await _access_map(db, user)
        user.access_map = access_map
    return access_map.get(project_id, ())


async def accessible_project_ids(db: AsyncSession, user: User):
    """Return projects reached by direct or group entries, or None for an administrator."""
    if user.role == UserRole.admin:
        return None
    access_map = getattr(user, "access_map", None)
    if access_map is None:
        access_map = await _access_map(db, user)
        user.access_map = access_map
    return [project_id for project_id, terms in access_map.items() if terms]


def customer_only(user: User, project_id: int) -> bool:
    """Identify the stored external account for retained external workflow restrictions."""
    return user.role == UserRole.external


async def is_customer_only(db: AsyncSession, user: User, project_id: int) -> bool:
    """Identify an external account independently of its policy visibility scope."""
    return customer_only(user, project_id)


def term_type_allows(term: AccessTerm, action: str, type_code: Optional[str]) -> bool:
    """Whether the term grants the action on the type and covers that document type."""
    if (
        type_code in DOC_TYPE_RESOURCES
        and term.doc_types is not None
        and type_code not in term.doc_types
    ):
        return False
    return has_permission(term.permissions, action, type_code)


def _row_type_code(row) -> Optional[str]:
    """The document type code of an artefact row."""
    key = TAG_TYPE_OF_MODEL.get(type(row))
    if key is None:
        return None
    return TYPE_CODES[key] or getattr(row, "doc_type", None)


async def _row_tag_ids(db: AsyncSession, row) -> Optional[frozenset]:
    """The tag ids the row carries; None for a kind that carries no tags."""
    key = TAG_TYPE_OF_MODEL.get(type(row))
    if key is None:
        return None
    found = await db.execute(
        select(ArtefactTag.tag_id).where(
            ArtefactTag.artefact_type == key, ArtefactTag.artefact_id == row.id
        )
    )
    return frozenset(found.scalars().all())


def _term_covers(term: AccessTerm, visibility, type_code: Optional[str], row_tags) -> bool:
    """Whether the term covers a row of the visibility, document type and tags: the type is
    one of the term's and the row carries one of the tags the term ticks, its visibility
    counting as a tag. A row without a visibility counts as carrying either."""
    if (
        type_code in DOC_TYPE_RESOURCES
        and term.doc_types is not None
        and type_code not in term.doc_types
    ):
        return False
    visibility = getattr(visibility, "value", visibility)
    if term.customer_only and visibility not in (None, ArtefactVisibility.customer.value):
        return False
    if term.visibilities is None:
        return True
    if visibility is None and term.visibilities:
        return True
    if visibility in term.visibilities:
        return True
    return bool(row_tags and term.tags & row_tags)


async def row_allows(
    db: AsyncSession,
    user: User,
    row,
    action: str,
    resource: Optional[str] = None,
    *,
    visibility: Optional[str] = None,
) -> bool:
    """Whether one term of the user on the row's project grants the action on the row's
    type and covers the row (R-u); always for an administrator. ``visibility``, when
    given, is used in place of the row's own."""
    if user.role == UserRole.admin:
        return True
    if user.role == UserRole.external and resource == "parameter":
        return False
    terms = await access_terms(db, user, row.project_id)
    if not terms:
        return False
    type_code = resource if resource is not None else _row_type_code(row)
    row_tags = None
    if any(term.tags for term in terms):
        row_tags = await _row_tag_ids(db, row)
    shown = visibility if visibility is not None else getattr(row, "visibility", None)
    return any(
        has_permission(term.permissions, action, type_code)
        and _term_covers(term, shown, type_code, row_tags)
        for term in terms
    )


def creating_terms(user: User, project_id: int, type_code: str) -> tuple:
    """The terms of the user on the project that grant create on the type; read from the
    user's loaded access map."""
    access_map = getattr(user, "access_map", None) or {}
    return tuple(
        term
        for term in access_map.get(project_id, ())
        if term_type_allows(term, "create", type_code)
    )


async def creation_covered(
    db: AsyncSession,
    user: User,
    project_id: int,
    type_code: Optional[str],
    visibility,
    tag_ids,
    action: str = "create",
) -> bool:
    """Whether one term of the user grants the action on the type in the project and covers
    a new row of the visibility with the given tags, and every given tag is one those terms
    tick."""
    if user.role == UserRole.admin:
        return True
    given = frozenset(tag_ids)
    terms = [
        term
        for term in await access_terms(db, user, project_id)
        if term_type_allows(term, action, type_code)
    ]
    if not any(_term_covers(term, visibility, type_code, given) for term in terms):
        return False
    if any(term.visibilities is None for term in terms):
        return True
    return given <= frozenset().union(*(term.tags for term in terms))


async def creation_allowed(db: AsyncSession, user: User, row, tag_ids, action="create") -> bool:
    """Whether ``creation_covered`` holds for the new row's project, type and visibility."""
    return await creation_covered(
        db,
        user,
        row.project_id,
        _row_type_code(row),
        getattr(row, "visibility", None),
        tag_ids,
        action,
    )


async def covers_with_tags(db: AsyncSession, user: User, row, action: str, tag_ids) -> bool:
    """Whether one term of the user grants the action on the row's type and covers the row
    when it carries the given tags."""
    if user.role == UserRole.admin:
        return True
    type_code = _row_type_code(row)
    return any(
        term_type_allows(term, action, type_code)
        and _term_covers(term, getattr(row, "visibility", None), type_code, frozenset(tag_ids))
        for term in await access_terms(db, user, row.project_id)
    )


async def get_external_doc_types(
    db: AsyncSession, current_user: User, project_id: int
) -> Optional[set[str]]:
    """The document types the user's terms on the project cover (None: every type);
    403 for a user with no access there."""
    if current_user.role == UserRole.admin:
        return None
    terms = await access_terms(db, current_user, project_id)
    if not terms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to this project.",
        )
    allowed: set[str] = set()
    for term in terms:
        if term.doc_types is None:
            return None
        allowed.update(code for code in term.doc_types if term_type_allows(term, "view", code))
    return allowed


async def require_external_doc_type_access(
    db: AsyncSession,
    current_user: User,
    project_id: int,
    doc_type: str,
) -> None:
    """403 when no term of the user on the project covers the document type."""
    if not await doc_type_visible(db, current_user, project_id, doc_type):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized for document type '{doc_type}'.",
        )


def external_doc_type_allowed(
    current_user: User,
    allowed_doc_types: Optional[set[str]],
    doc_type: str,
) -> bool:
    """Whether the document type is in the set from ``get_external_doc_types``."""
    return allowed_doc_types is None or doc_type in allowed_doc_types


async def doc_type_visible(
    db: AsyncSession, current_user: User, project_id: int, doc_type: str
) -> bool:
    """Whether some term of the user on the project covers the document type."""
    return external_doc_type_allowed(
        current_user, await get_external_doc_types(db, current_user, project_id), doc_type
    )


def _carries(model, tag_type: str, tags) -> object:
    """An EXISTS on the row carrying one of the tags."""
    return (
        select(ArtefactTag.id)
        .where(
            ArtefactTag.artefact_type == tag_type,
            ArtefactTag.artefact_id == model.id,
            ArtefactTag.tag_id.in_(sorted(tags)),
        )
        .exists()
    )


def _term_condition(term: AccessTerm, model) -> object:
    """The SQL condition for the rows of the model the term lets the user see."""
    tag_type = TAG_TYPE_OF_MODEL.get(model)
    fixed_type = TYPE_CODES.get(tag_type) if tag_type else None
    parts = []
    if tag_type and fixed_type is None and hasattr(model, "doc_type"):
        kinds = [kind for kind in CANONICAL_DOCUMENT_KINDS if term_type_allows(term, "view", kind)]
        if not kinds:
            return false()
        parts.append(model.doc_type.in_(kinds))
    elif fixed_type is not None and not term_type_allows(term, "view", fixed_type):
        return false()
    if hasattr(model, "visibility"):
        if term.customer_only:
            parts.append(model.visibility == ArtefactVisibility.customer.value)
        if term.visibilities is not None:
            covered = []
            if term.visibilities:
                covered.append(model.visibility.in_(sorted(term.visibilities)))
            if term.tags and tag_type:
                covered.append(_carries(model, tag_type, term.tags))
            if not covered:
                return false()
            parts.append(or_(*covered))
    return and_(*parts) if parts else true()


def apply_external_visibility_filter(query, model, current_user: User):
    """The query limited to the rows the user may see: rows of the projects the user
    reaches that one of their terms there covers (R-u). Nothing for a user whose access
    map is not loaded; no limit for an administrator."""
    if current_user.role == UserRole.admin:
        return query
    access_map = getattr(current_user, "access_map", None)
    if not access_map:
        return query.where(false())
    return query.where(
        or_(
            *(
                and_(
                    model.project_id == project_id,
                    or_(*(_term_condition(term, model) for term in terms)),
                )
                for project_id, terms in access_map.items()
            )
        )
    )


async def tag_scope(
    db: AsyncSession,
    current_user: User,
    project_id: int,
    type_code: Optional[str] = None,
    action: str = "view",
):
    """The further tags the user's terms on the project tick, for the document type and
    the action when a type is given; None means every tag."""
    if current_user.role == UserRole.admin:
        return None
    tags: set = set()
    for term in await access_terms(db, current_user, project_id):
        if type_code is not None and not term_type_allows(term, action, type_code):
            continue
        if term.visibilities is None:
            return None
        tags.update(term.tags)
    return frozenset(tags)


async def effective_permissions(
    db: AsyncSession, current_user: User, project_id: Optional[int]
) -> Permissions:
    """Union the scope's policy matrices; route identity and workflow gates still apply."""
    if current_user.role == UserRole.admin:
        return role_baseline(current_user.role.value, None)
    permissions: Permissions = {}
    for term in await access_terms(db, current_user, project_id):
        merge(permissions, {r: sorted(a) for r, a in term.permissions.items()})
    if current_user.role == UserRole.external:
        permissions = {
            resource: permissions.get(resource, set()) | permissions.get(ANY, set())
            for resource in (APP_RESOURCES if project_id is None else RESOURCES)
            if resource != "parameter" and (permissions.get(resource) or permissions.get(ANY))
        }
    return permissions


async def holds_on_project(
    db: AsyncSession, current_user: User, project_id: int, action: str, resource: Optional[str]
) -> bool:
    """Whether one term of the user on the project grants the action on the resource."""
    if current_user.role == UserRole.admin:
        return True
    if current_user.role == UserRole.external and resource == "parameter":
        return False
    return any(
        term_type_allows(term, action, resource)
        for term in await access_terms(db, current_user, project_id)
    )


async def user_can_access_project(db: AsyncSession, current_user: User, project_id: int) -> bool:
    """Whether the user has an access entry reaching the project."""
    if current_user.role == UserRole.admin:
        return True
    return bool(await access_terms(db, current_user, project_id))


async def require_project_access(
    db: AsyncSession,
    current_user: User,
    project_id: int,
    *,
    permission: Optional[tuple[str, str]] = None,
    outsider: Optional[HTTPException] = None,
) -> None:
    """Admit the user to the project or raise.

    A user with no access entry reaching the project gets ``outsider`` or 403 "User is
    not assigned to this project."; with ``permission=(action, resource)`` one term must
    grant the action on the resource, else 403 "Missing permission".
    """
    not_assigned = outsider or HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User is not assigned to this project.",
    )
    if current_user.role == UserRole.admin:
        project = await db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return None
    terms = await access_terms(db, current_user, project_id)
    if not terms:
        raise not_assigned
    if permission is not None:
        action, resource = permission
        if not await holds_on_project(db, current_user, project_id, action, resource):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {action} on {resource}.",
            )
    return None


def require_permission(action: str, resource: str):
    """FastAPI dependency for a route with a ``project_id`` path parameter: the user's
    effective permissions on that project allow the action on the resource."""

    async def permission_checker(
        project_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db, scope="function"),
    ) -> User:
        if current_user.role == UserRole.admin:
            return current_user
        await require_project_access(db, current_user, project_id, permission=(action, resource))
        return current_user

    return permission_checker


def require_app_permission(action: str, resource: str = "access"):
    """Require the requested operation on an application resource."""

    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db, scope="function"),
    ) -> User:
        permissions = await effective_permissions(db, current_user, None)
        if not has_permission(permissions, action, resource):
            raise HTTPException(status_code=403, detail="Application permission is required")
        return current_user

    return permission_checker
