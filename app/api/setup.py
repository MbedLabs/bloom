"""First-run setup: create the very first administrator.

_SETUP_LOCK_KEY is the fixed PostgreSQL advisory lock key of the first-admin bootstrap.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import limiter
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.schemas.auth import GenericMessageResponse
from app.schemas.setup import CreateFirstAdminRequest, SetupStatusResponse
from app.services.audit import record_audit_event
from app.services.mail_service import MailConfigurationError, send_admin_welcome_email

logger = logging.getLogger(__name__)

router = APIRouter()

_SETUP_LOCK_KEY = 8_314_502_120


async def _user_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(User))
    return int(result.scalar_one())


@router.get("/setup/status")
async def setup_status(
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> SetupStatusResponse:
    """Report whether the instance still needs its first administrator."""
    return SetupStatusResponse(setup_required=await _user_count(db) == 0)


@router.post(
    "/setup",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def create_first_admin(
    request: Request,
    data: CreateFirstAdminRequest,
    db: Annotated[AsyncSession, Depends(get_db, scope="function")],
) -> GenericMessageResponse:
    """Create the first administrator, once, on an instance that has no users.

    On PostgreSQL a transaction-scoped advisory lock serialises concurrent attempts. An instance
    with a user answers 409. The welcome email is best effort: a mail configuration error is logged
    and setup still succeeds.
    """
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _SETUP_LOCK_KEY})

    if await _user_count(db) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This instance has already been set up.",
        )

    admin = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    await record_audit_event(
        db,
        "setup.first_admin_created",
        actor_type="anonymous",
        target_type="user",
        target_id=admin.id,
        details={"email": admin.email},
    )
    await db.commit()

    logger.info("First administrator created via setup flow: %s", data.email)

    try:
        send_admin_welcome_email(
            to_email=admin.email,
            full_name=admin.full_name,
            login_link=f"{settings.APP_BASE_URL.rstrip('/')}/login",
        )
    except MailConfigurationError as exc:
        logger.warning("Administrator created but the confirmation email failed: %s", exc)

    return GenericMessageResponse(message="Administrator account created. You can now sign in.")
