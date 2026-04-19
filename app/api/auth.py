"""
Auth API endpoints: login, get current user, update profile.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import limiter
from app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.models.user_token import UserTokenPurpose
from app.schemas.auth import (
    AcceptInviteRequest,
    AcceptInviteResponse,
    ForgotPasswordRequest,
    GenericMessageResponse,
    InviteInfoResponse,
    LoginRequest,
    PasswordChange,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    UserUpdate,
    VerifyEmailRequest,
)
from app.services.mail_service import (
    MailConfigurationError,
    send_password_reset_email,
    send_verification_email,
)
from app.services.token_service import (
    TokenValidationError,
    create_user_token,
    find_token,
    get_valid_token,
    mark_token_used,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.email is not None:
        existing = await db.execute(
            select(User).where(User.email == data.email, User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = data.email

    await db.flush()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.put("/me/password", response_model=UserResponse)
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.password_set_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.get("/invite-info", response_model=InviteInfoResponse)
async def get_invite_info(token: str, db: AsyncSession = Depends(get_db)):
    user_token = await find_token(db, token=token, purpose=UserTokenPurpose.invite)
    if user_token is None:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = await db.get(User, user_token.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    expired = user_token.expires_at < datetime.now(timezone.utc)
    used = user_token.used_at is not None
    return InviteInfoResponse(
        email=user.email,
        full_name=user.full_name,
        valid=not expired and not used,
        expired=expired,
    )


@router.post("/accept-invite", response_model=AcceptInviteResponse)
async def accept_invite(data: AcceptInviteRequest, db: AsyncSession = Depends(get_db)):
    try:
        user_token = await get_valid_token(db, token=data.token, purpose=UserTokenPurpose.invite)
    except TokenValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc

    user = await db.get(User, user_token.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.invite_accepted_at is not None:
        raise HTTPException(status_code=400, detail="Invite already accepted")

    user.hashed_password = get_password_hash(data.password)
    now = datetime.now(timezone.utc)
    user.invite_accepted_at = now
    user.password_set_at = now
    await mark_token_used(db, user_token)

    verification_token = await create_user_token(
        db,
        user_id=user.id,
        purpose=UserTokenPurpose.email_verification,
        ttl_hours=settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS,
    )
    verification_link = (
        f"{settings.FRONTEND_BASE_URL.rstrip('/')}/verify-email?token={verification_token}"
    )

    try:
        send_verification_email(
            to_email=user.email,
            full_name=user.full_name,
            verification_link=verification_link,
        )
    except MailConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    await db.flush()
    return AcceptInviteResponse(
        email=user.email,
        message="Invite accepted. Verification email sent.",
    )


@router.post("/verify-email", response_model=GenericMessageResponse)
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    try:
        user_token = await get_valid_token(
            db,
            token=data.token,
            purpose=UserTokenPurpose.email_verification,
        )
    except TokenValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc

    user = await db.get(User, user_token.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified_at is not None:
        raise HTTPException(status_code=400, detail="Email already verified")

    user.email_verified_at = datetime.now(timezone.utc)
    await mark_token_used(db, user_token)
    await db.flush()
    return GenericMessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=GenericMessageResponse)
@limiter.limit("5/hour")
async def resend_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.email_verified_at is not None:
        raise HTTPException(status_code=400, detail="Email already verified")

    verification_token = await create_user_token(
        db,
        user_id=current_user.id,
        purpose=UserTokenPurpose.email_verification,
        ttl_hours=settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS,
    )
    verification_link = (
        f"{settings.FRONTEND_BASE_URL.rstrip('/')}/verify-email?token={verification_token}"
    )

    try:
        send_verification_email(
            to_email=current_user.email,
            full_name=current_user.full_name,
            verification_link=verification_link,
        )
    except MailConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    await db.flush()
    return GenericMessageResponse(message="Verification email sent")


@router.post("/forgot-password", response_model=GenericMessageResponse)
@limiter.limit("5/hour")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    response = GenericMessageResponse(
        message="If the account exists, a password reset email has been sent"
    )

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return response

    reset_token = await create_user_token(
        db,
        user_id=user.id,
        purpose=UserTokenPurpose.password_reset,
        ttl_hours=settings.PASSWORD_RESET_TOKEN_TTL_HOURS,
    )
    reset_link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={reset_token}"

    try:
        send_password_reset_email(
            to_email=user.email,
            full_name=user.full_name,
            reset_link=reset_link,
        )
    except MailConfigurationError:
        logger.exception("Password reset email could not be sent for user_id=%s", user.id)

    await db.flush()
    return response


@router.post("/reset-password", response_model=GenericMessageResponse)
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        user_token = await get_valid_token(
            db,
            token=data.token,
            purpose=UserTokenPurpose.password_reset,
        )
    except TokenValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc

    user = await db.get(User, user_token.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(data.new_password)
    user.password_set_at = datetime.now(timezone.utc)
    await mark_token_used(db, user_token)
    await db.flush()
    return GenericMessageResponse(message="Password reset successfully")
