"""
Security utilities: password hashing, JWT token creation/verification, auth dependencies.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.permissions import Permissions, has_permission, merge, role_baseline
from app.models import ArtefactVisibility, Project
from app.models.groups import Group, GroupMembership, GroupProjectGrant, Policy
from app.models.project_membership import ProjectExternalDocType, ProjectMembership
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
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> User:
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
    except (JWTError, TypeError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == entity_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    # Reject tokens minted before a password/reset/email-change bumped the user's
    # session_version.
    if payload.get("ver") != user.session_version:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )
    set_audit_actor("user", user.id)
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


async def _get_project_membership(
    db: AsyncSession, user_id: int, project_id: int
) -> Optional[ProjectMembership]:
    result = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.user_id == user_id,
            ProjectMembership.project_id == project_id,
        )
    )
    return result.scalar_one_or_none()


async def get_external_doc_types(
    db: AsyncSession, current_user: User, project_id: int
) -> Optional[set[str]]:
    """Return allowed document types for an external member."""
    if current_user.role == UserRole.admin:
        return None

    membership = await _get_project_membership(db, current_user.id, project_id)
    if membership is None:
        group_role = await _group_project_role(db, current_user.id, project_id)
        if group_role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not assigned to this project.",
            )
        if current_user.role != UserRole.external:
            return None
        return await _group_doc_type_scope(db, current_user.id, project_id)

    if current_user.role != UserRole.external:
        return None

    result = await db.execute(
        select(ProjectExternalDocType.doc_type).where(
            ProjectExternalDocType.membership_id == membership.id
        )
    )
    return set(result.scalars().all())


async def require_external_doc_type_access(
    db: AsyncSession,
    current_user: User,
    project_id: int,
    doc_type: str,
) -> None:
    """Enforce the external member document-type allowlist for a project."""
    allowed = await get_external_doc_types(db, current_user, project_id)
    if allowed is not None and doc_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"External user is not authorized for document type '{doc_type}'.",
        )


def external_doc_type_allowed(
    current_user: User,
    allowed_doc_types: Optional[set[str]],
    doc_type: str,
) -> bool:
    if current_user.role != UserRole.external:
        return True
    return allowed_doc_types is None or doc_type in allowed_doc_types


def apply_external_visibility_filter(query, model, current_user: User):
    if current_user.role == UserRole.external:
        query = query.where(model.visibility == ArtefactVisibility.customer.value)
    return query


_ROLE_STRENGTH = {"external": 1, "maintainer": 2, "admin": 3}


async def _group_policy_values(db: AsyncSession, user_id: int, project_id: int, column) -> list:
    """One column of every policy that reaches this user on this project through a
    group grant. A grant with a NULL project is an all-projects grant."""
    result = await db.execute(
        select(column)
        .select_from(GroupMembership)
        .join(Group, Group.id == GroupMembership.group_id)
        .join(GroupProjectGrant, GroupProjectGrant.group_id == Group.id)
        .join(Policy, Policy.id == Group.policy_id)
        .where(
            GroupMembership.user_id == user_id,
            (GroupProjectGrant.project_id == project_id) | (GroupProjectGrant.project_id.is_(None)),
        )
    )
    return list(result.scalars().all())


async def _group_project_role(db: AsyncSession, user_id: int, project_id: int) -> Optional[str]:
    """Strongest policy base_role from the user's groups granted this project."""
    roles = [r for r in await _group_policy_values(db, user_id, project_id, Policy.base_role) if r]
    if not roles:
        return None
    return max(roles, key=lambda r: _ROLE_STRENGTH.get(r, 0))


async def _group_doc_type_scope(
    db: AsyncSession, user_id: int, project_id: int
) -> Optional[set[str]]:
    """Allowed external document types from the user's groups granted this project.

    Unions the doc_tag_scope of every applicable group policy. A policy whose scope
    is NULL grants every type, so the union collapses to None (no restriction).
    """
    scopes = await _group_policy_values(db, user_id, project_id, Policy.doc_tag_scope)
    allowed: set[str] = set()
    for scope in scopes:
        if scope is None:
            return None
        allowed.update(scope)
    return allowed


async def _effective_permissions(
    db: AsyncSession,
    current_user: User,
    project_id: int,
    membership: Optional[ProjectMembership],
) -> Permissions:
    permissions = role_baseline(current_user.role.value, membership.role if membership else None)
    for policy in await _group_policy_values(db, current_user.id, project_id, Policy):
        seen: set[int] = set()
        current: Optional[Policy] = policy
        while current is not None and current.id not in seen:
            seen.add(current.id)
            merge(permissions, current.permissions)
            current = await db.get(Policy, current.parent_id) if current.parent_id else None
    return permissions


async def effective_permissions(
    db: AsyncSession, current_user: User, project_id: int
) -> Permissions:
    """The user's permissions on a project: the role baseline plus every policy of the
    user's groups granted the project, each with the policies it inherits from."""
    if current_user.role == UserRole.admin:
        return role_baseline(current_user.role.value, None)
    membership = await _get_project_membership(db, current_user.id, project_id)
    return await _effective_permissions(db, current_user, project_id, membership)


async def user_can_access_project(
    db: AsyncSession, current_user: User, project_id: int, *, roles: Optional[set[str]] = None
) -> bool:
    if current_user.role == UserRole.admin:
        return True
    membership = await _get_project_membership(db, current_user.id, project_id)
    if membership is not None and (
        roles is None or (membership.role in roles and current_user.role.value in roles)
    ):
        return True
    group_role = await _group_project_role(db, current_user.id, project_id)
    return group_role is not None and (roles is None or group_role in roles)


async def require_project_access(
    db: AsyncSession,
    current_user: User,
    project_id: int,
    *,
    roles: Optional[set[str]] = None,
    permission: Optional[tuple[str, str]] = None,
) -> ProjectMembership | None:
    """Admit the user to the project or raise 403.

    With ``permission=(action, resource)`` the check is the effective permission set
    (role baseline plus group policies); with ``roles`` it is the role gate.
    """
    if current_user.role == UserRole.admin:
        project = await db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return None

    membership = await _get_project_membership(db, current_user.id, project_id)
    if permission is not None:
        permissions = await _effective_permissions(db, current_user, project_id, membership)
        action, resource = permission
        if has_permission(permissions, action, resource):
            return membership
        if not permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not assigned to this project.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {action} on {resource}.",
        )
    if membership is not None and (
        roles is None or (membership.role in roles and current_user.role.value in roles)
    ):
        return membership
    group_role = await _group_project_role(db, current_user.id, project_id)
    if group_role is not None and (roles is None or group_role in roles):
        return None
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to this project.",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"User is not assigned to this project with one of: {sorted(roles)}.",
    )


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
