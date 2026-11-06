"""Approve and exchange PKCE sessions using Bloom's existing user credentials.

A refused step raises CliAuthorizationError with one of the rejection codes below; the routes
record that code in a failure audit event and answer with a generic message.
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy import delete, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.permissions import as_lists
from app.core.security import create_access_token, effective_permissions
from app.models.cli_auth_session import CliAuthSession
from app.models.user import User
from app.models.user_token import UserTokenPurpose
from app.schemas.auth import UserResponse
from app.schemas.cli_auth import (
    CliCallbackApproval,
    CliCallbackDenial,
    CliCodeApproval,
    CliCodeDenial,
    CliExchangeRequest,
    CliStartRequest,
    CliTokenResponse,
    validate_loopback_redirect,
)
from app.services.token_service import (
    TokenValidationError,
    claim_token,
    create_user_token,
    find_token,
    hash_token,
)

SESSION_LIFETIME = timedelta(minutes=10)

NOT_PENDING = "not_pending"
NOT_APPROVED = "unknown_or_unapproved_session"
CODE_OR_VERIFIER_MISMATCH = "code_or_verifier_mismatch"
INACTIVE_OR_CHANGED_USER = "inactive_or_changed_user"
EXPIRED_OR_CONSUMED = "expired_or_consumed"
INVALID_REFRESH_TOKEN = "invalid_token"
INACTIVE_OR_MISSING_USER = "inactive_or_missing_user"
CODE_MODE_DISABLED = "code_mode_disabled"
CODE_MISMATCH = "request_code_mismatch"

REQUEST_CODE_BYTES = 5
REQUEST_CODE_LETTERS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


class CliAuthorizationError(Exception):
    """A refused authorization step with its rejection code and, when known, the account id."""

    def __init__(self, reason: str, user_id: int | None = None):
        self.reason = reason
        self.user_id = user_id
        super().__init__(reason)


def utcnow() -> datetime:
    """Return the database's naive UTC timestamp."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def code_mode_refused(mode: str) -> bool:
    """Return whether this instance refuses a request in the given mode."""
    return mode == "code" and not settings.CLI_CODE_MODE_ENABLED


def request_code(code_challenge: str) -> str:
    """Return the XXXX-XXXX request code of a PKCE challenge.

    The code is the RFC 4648 base32 text of the first five bytes of the challenge's SHA-256.
    """
    digest = hashlib.sha256(code_challenge.encode("ascii")).digest()[:REQUEST_CODE_BYTES]
    letters = base64.b32encode(digest).decode("ascii")
    return f"{letters[:4]}-{letters[4:]}"


def typed_code_matches(typed: str, code_challenge: str) -> bool:
    """Return whether a typed request code, in any case and with spaces or hyphens, matches.

    A value that is not exactly eight characters from A-Z and 2-7 never matches.
    """
    letters = typed.upper().replace(" ", "").replace("-", "")
    expected = request_code(code_challenge).replace("-", "")
    if len(letters) != len(expected) or not set(letters) <= REQUEST_CODE_LETTERS:
        return False
    return secrets.compare_digest(letters, expected)


def pending_conditions(session_id: UUID) -> tuple:
    """Return the filters selecting one unexpired request that is not approved or exchanged."""
    return (
        CliAuthSession.id == session_id,
        CliAuthSession.expires_at > utcnow(),
        CliAuthSession.consumed_at.is_(None),
        CliAuthSession.exchange_code_hash.is_(None),
        CliAuthSession.user_id.is_(None),
    )


async def purge_finished_sessions(db: AsyncSession, now: datetime) -> None:
    """Delete the authorization sessions that have expired or been exchanged."""
    await db.execute(
        delete(CliAuthSession).where(
            or_(CliAuthSession.expires_at <= now, CliAuthSession.consumed_at.is_not(None))
        )
    )


async def start_session(db: AsyncSession, data: CliStartRequest) -> CliAuthSession:
    """Delete finished sessions, then create one pending session for ten minutes.

    A manual-code request is refused with code_mode_disabled while code sign-in is off.
    """
    if code_mode_refused(data.mode):
        raise CliAuthorizationError(CODE_MODE_DISABLED)
    now = utcnow()
    await purge_finished_sessions(db, now)
    session = CliAuthSession(**data.model_dump(), created_at=now, expires_at=now + SESSION_LIFETIME)
    db.add(session)
    await db.flush()
    return session


async def pending_session(db: AsyncSession, session_id: UUID) -> CliAuthSession:
    """Load an unexpired request that has not been approved or exchanged.

    A stored manual-code request is refused with code_mode_disabled while code sign-in is off.
    """
    session = await db.get(CliAuthSession, session_id)
    if session is not None and code_mode_refused(session.mode):
        raise CliAuthorizationError(CODE_MODE_DISABLED)
    if (
        session is None
        or session.expires_at <= utcnow()
        or session.consumed_at is not None
        or session.exchange_code_hash is not None
        or session.user_id is not None
    ):
        raise CliAuthorizationError(NOT_PENDING)
    return session


async def check_request_code(db: AsyncSession, session_id: UUID, typed: str) -> CliAuthSession:
    """Return the pending request when the typed request code matches; nothing is written.

    A mismatch raises request_code_mismatch; the request stays pending.
    """
    session = await pending_session(db, session_id)
    if not typed_code_matches(typed, session.code_challenge):
        raise CliAuthorizationError(CODE_MISMATCH)
    return session


async def approve_session(
    db: AsyncSession, session_id: UUID, user: User, typed: str
) -> tuple[CliAuthSession, str]:
    """Bind one pending request to the locked, active approving account and a code digest.

    The typed request code is checked first.
    """
    await check_request_code(db, session_id, typed)
    version = user.session_version
    current = await db.get(
        User, user.id, populate_existing=True, with_for_update={"key_share": True}
    )
    if current is None or not current.is_active or current.session_version != version:
        raise CliAuthorizationError(INACTIVE_OR_CHANGED_USER)
    code = secrets.token_urlsafe(32)
    result = await db.execute(
        update(CliAuthSession)
        .where(*pending_conditions(session_id))
        .values(
            exchange_code_hash=hash_token(code),
            user_id=current.id,
            approved_session_version=current.session_version,
        )
        .returning(CliAuthSession)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise CliAuthorizationError(NOT_PENDING)
    return session, code


async def deny_session(db: AsyncSession, session_id: UUID) -> CliAuthSession:
    """Delete one pending request and return the deleted row."""
    result = await db.execute(
        delete(CliAuthSession).where(*pending_conditions(session_id)).returning(CliAuthSession)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise CliAuthorizationError(NOT_PENDING)
    return session


def loopback_target(session: CliAuthSession, name: str, value: str) -> str:
    """Return the stored loopback callback, validated again, with one parameter and the state."""
    try:
        target = urlsplit(validate_loopback_redirect(session.redirect_uri))
    except (ValueError, TypeError) as exc:
        raise CliAuthorizationError(NOT_PENDING) from exc
    query = parse_qsl(target.query, keep_blank_values=True) + [
        (name, value),
        ("state", session.state),
    ]
    return urlunsplit(target._replace(query=urlencode(query)))


def approval_response(session: CliAuthSession, code: str) -> CliCallbackApproval | CliCodeApproval:
    """Return the manual code, or the stored loopback callback carrying the code and state."""
    if session.mode != "callback":
        return CliCodeApproval(exchange_code=code, expires_at=session.expires_at)
    return CliCallbackApproval(redirect_to=loopback_target(session, "code", code))


def denial_response(session: CliAuthSession) -> CliCallbackDenial | CliCodeDenial:
    """Return the denial answer: empty for a manual-code request, else the loopback callback.

    The callback carries error=access_denied and the stored state.
    """
    if session.mode != "callback":
        return CliCodeDenial()
    return CliCallbackDenial(redirect_to=loopback_target(session, "error", "access_denied"))


async def issue_credentials(db: AsyncSession, user: User) -> CliTokenResponse:
    """Issue one refresh row and an access JWT bound to its live identity."""
    refresh_token = await create_user_token(
        db,
        user_id=user.id,
        purpose=UserTokenPurpose.refresh,
        ttl_hours=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24,
        invalidate_existing=False,
    )
    refresh_row = await find_token(db, token=refresh_token, purpose=UserTokenPurpose.refresh)
    access_token = create_access_token(
        {
            "sub": str(user.id),
            "type": "user",
            "ver": user.session_version,
            "cli_refresh_id": refresh_row.id,
        }
    )
    user.application_permissions = as_lists(await effective_permissions(db, user, None))
    return CliTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


def pkce_challenge(verifier: str) -> str:
    """Return the S256 PKCE challenge of a verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


async def exchange_session(db: AsyncSession, data: CliExchangeRequest) -> CliTokenResponse:
    """Consume an approved code once after validating PKCE and the account version.

    A stored manual-code request is refused with code_mode_disabled while code sign-in is off.
    """
    session = await db.get(CliAuthSession, data.session_id)
    if session is not None and code_mode_refused(session.mode):
        raise CliAuthorizationError(CODE_MODE_DISABLED)
    if session is None or session.user_id is None or session.exchange_code_hash is None:
        raise CliAuthorizationError(NOT_APPROVED)
    code_matches = secrets.compare_digest(hash_token(data.code), session.exchange_code_hash)
    verifier_matches = secrets.compare_digest(
        pkce_challenge(data.code_verifier), session.code_challenge
    )
    if not code_matches or not verifier_matches:
        raise CliAuthorizationError(CODE_OR_VERIFIER_MISMATCH)
    user = await db.get(
        User, session.user_id, populate_existing=True, with_for_update={"key_share": True}
    )
    if (
        user is None
        or not user.is_active
        or user.session_version != session.approved_session_version
    ):
        raise CliAuthorizationError(INACTIVE_OR_CHANGED_USER)
    now = utcnow()
    result = await db.execute(
        update(CliAuthSession)
        .where(
            CliAuthSession.id == session.id,
            CliAuthSession.user_id == user.id,
            CliAuthSession.approved_session_version == user.session_version,
            CliAuthSession.exchange_code_hash == hash_token(data.code),
            CliAuthSession.expires_at > now,
            CliAuthSession.consumed_at.is_(None),
        )
        .values(consumed_at=now)
        .returning(CliAuthSession.id)
    )
    if result.scalar_one_or_none() is None:
        raise CliAuthorizationError(EXPIRED_OR_CONSUMED)
    return await issue_credentials(db, user)


async def refresh_credentials(db: AsyncSession, token: str) -> CliTokenResponse:
    """Consume a refresh token through claim_token and issue replacement credentials.

    Every unused, unexpired token of purpose refresh is accepted, the same pool the browser
    refresh cookie and invalidate_all_refresh_tokens use.
    """
    candidate = await find_token(db, token=token, purpose=UserTokenPurpose.refresh)
    if candidate is None:
        raise CliAuthorizationError(INVALID_REFRESH_TOKEN)
    user = await db.get(
        User, candidate.user_id, populate_existing=True, with_for_update={"key_share": True}
    )
    if user is None or not user.is_active:
        raise CliAuthorizationError(INACTIVE_OR_MISSING_USER, candidate.user_id)
    try:
        claimed = await claim_token(db, token=token, purpose=UserTokenPurpose.refresh)
    except TokenValidationError as exc:
        raise CliAuthorizationError(INVALID_REFRESH_TOKEN, user.id) from exc
    if claimed.user_id != user.id:
        raise CliAuthorizationError(INVALID_REFRESH_TOKEN, user.id)
    return await issue_credentials(db, user)
