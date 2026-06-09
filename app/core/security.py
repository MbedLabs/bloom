"""
Security utilities: password hashing, JWT token creation/verification, auth dependencies.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import Project
from app.models.project_membership import ProjectMembership
from app.models.user import User, UserRole

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
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    # Verify JTI if this is an API token
    if payload.get("type") == "api_token":
        if user.api_token_jti != payload.get("jti"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API token has been invalidated",
            )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )
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


async def user_can_access_project(
    db: AsyncSession, current_user: User, project_id: int, *, roles: Optional[set[str]] = None
) -> bool:
    if current_user.role == UserRole.admin:
        return True
    membership = await _get_project_membership(db, current_user.id, project_id)
    if membership is None:
        return False
    if roles is None:
        return True
    return membership.role in roles and current_user.role.value in roles


async def require_project_access(
    db: AsyncSession,
    current_user: User,
    project_id: int,
    *,
    roles: Optional[set[str]] = None,
) -> ProjectMembership | None:
    if current_user.role == UserRole.admin:
        project = await db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return None

    membership = await _get_project_membership(db, current_user.id, project_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to this project.",
        )
    if roles is not None and (membership.role not in roles or current_user.role.value not in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User is not assigned to this project with one of: {sorted(roles)}.",
        )
    return membership


class _ProjectRoleChecker:
    """Callable dependency that checks project-scoped roles.

    Admin always passes (global).
    Maintainer and external must have a project_memberships row for the project."""

    def __init__(self, *roles: str) -> None:
        self._roles = set(roles)  # 'admin','maintainer','external'

    async def __call__(
        self,
        project_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.role == UserRole.admin:
            return current_user
        if current_user.role.value not in self._roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' not authorized for this project.",
            )
        membership = await _get_project_membership(db, current_user.id, project_id)
        if membership is None or membership.role != current_user.role.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User is not assigned to this project with role '{current_user.role.value}'.",
            )
        return current_user


def require_project_role(*roles: str):
    """FastAPI dependency: user has the given role AND a project_membership row.

    Args:
        roles: 'admin', 'maintainer', 'external'

    Usage:
        @router.post("/{project_id}/items")
        async def create_item(
            project_id: int,
            current_user: User = Depends(require_project_role("admin", "maintainer")),
        ): ...
    """
    return _ProjectRoleChecker(*roles)
