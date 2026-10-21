"""Browser approval and rotating credentials for user-scoped CLI clients.

A refused approve, exchange or refresh rolls back the request's changes, records a failure
audit event with its rejection code and answers with a generic message.
"""

from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.cli_auth import (
    CliApproveRequest,
    CliCallbackApproval,
    CliCodeApproval,
    CliExchangeRequest,
    CliRefreshRequest,
    CliSessionResponse,
    CliStartRequest,
    CliStartResponse,
    CliTokenResponse,
)
from app.services import cli_auth
from app.services.audit import record_audit_event, record_audit_failure

router = APIRouter()

AUTH_CLI_APPROVE = "auth.cli_approve"
AUTH_CLI_EXCHANGE = "auth.cli_exchange"
AUTH_CLI_REFRESH = "auth.cli_refresh"
SESSION_TARGET = "cli_auth_session"
INVALID_AUTHORIZATION = (
    "Invalid or expired authorization. Request a new sign-in link from your client."
)
INVALID_SESSION = "Invalid or expired session"
NO_STORE = "no-store"
BAD_REQUEST = {400: {"description": HTTPStatus(400).phrase}}
UNAUTHORIZED = {401: {"description": HTTPStatus(401).phrase}}

Database = Annotated[AsyncSession, Depends(get_db, scope="function")]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def _rejection(
    db: AsyncSession,
    action: str,
    error: cli_auth.CliAuthorizationError,
    *,
    status_code: int,
    detail: str,
    **fields: Any,
) -> HTTPException:
    """Roll back the request, record the refused attempt and return the generic error answer."""
    await db.rollback()
    await record_audit_failure(db, action, details={"reason": error.reason}, **fields)
    return HTTPException(status_code=status_code, detail=detail)


@router.post("/start", response_model=CliStartResponse)
@limiter.limit("10/minute")
async def cli_start(request: Request, data: CliStartRequest, response: Response, db: Database):
    """Start a ten-minute browser authorization request without credentials."""
    response.headers["Cache-Control"] = NO_STORE
    session = await cli_auth.start_session(db, data)
    return CliStartResponse(
        session_id=session.id,
        authorize_url=f"/auth/cli?session_id={session.id}",
        expires_at=session.expires_at,
    )


@router.get("/sessions/{session_id}", response_model=CliSessionResponse, responses=BAD_REQUEST)
async def cli_session(
    session_id: UUID, response: Response, current_user: CurrentUser, db: Database
):
    """Show the signed-in user the client and destination awaiting their approval."""
    response.headers["Cache-Control"] = NO_STORE
    try:
        session = await cli_auth.pending_session(db, session_id)
    except cli_auth.CliAuthorizationError as exc:
        raise HTTPException(status_code=400, detail=INVALID_AUTHORIZATION) from exc
    return CliSessionResponse(
        session_id=session.id,
        client_name=session.client_name,
        mode=session.mode,
        redirect_uri=session.redirect_uri,
        expires_at=session.expires_at,
        consumed=session.consumed_at is not None,
    )


@router.post(
    "/approve",
    response_model=CliCallbackApproval | CliCodeApproval,
    responses=BAD_REQUEST,
)
async def cli_approve(
    data: CliApproveRequest, response: Response, current_user: CurrentUser, db: Database
):
    """Approve a request once as the signed-in user without adding permissions."""
    response.headers["Cache-Control"] = NO_STORE
    actor_id = current_user.id
    try:
        session, code = await cli_auth.approve_session(db, data.session_id, current_user)
        approval = cli_auth.approval_response(session, code)
    except cli_auth.CliAuthorizationError as exc:
        raise await _rejection(
            db,
            AUTH_CLI_APPROVE,
            exc,
            status_code=400,
            detail=INVALID_AUTHORIZATION,
            actor_user_id=actor_id,
            target_type=SESSION_TARGET,
            target_id=data.session_id,
        ) from exc
    await record_audit_event(
        db,
        AUTH_CLI_APPROVE,
        actor_user_id=actor_id,
        target_type=SESSION_TARGET,
        target_id=session.id,
    )
    return approval


@router.post("/exchange", response_model=CliTokenResponse, responses=BAD_REQUEST)
@limiter.limit("30/minute")
async def cli_exchange(
    request: Request, data: CliExchangeRequest, response: Response, db: Database
):
    """Exchange the one-time approved code and PKCE verifier for user credentials."""
    response.headers["Cache-Control"] = NO_STORE
    try:
        credentials = await cli_auth.exchange_session(db, data)
    except cli_auth.CliAuthorizationError as exc:
        raise await _rejection(
            db,
            AUTH_CLI_EXCHANGE,
            exc,
            status_code=400,
            detail=INVALID_AUTHORIZATION,
            target_type=SESSION_TARGET,
            target_id=data.session_id,
        ) from exc
    await record_audit_event(
        db,
        AUTH_CLI_EXCHANGE,
        actor_user_id=credentials.user.id,
        target_type=SESSION_TARGET,
        target_id=data.session_id,
    )
    return credentials


@router.post("/refresh", response_model=CliTokenResponse, responses=UNAUTHORIZED)
@limiter.limit("30/minute")
async def cli_refresh(request: Request, data: CliRefreshRequest, response: Response, db: Database):
    """Rotate one JSON refresh token while leaving browser cookies unchanged."""
    response.headers["Cache-Control"] = NO_STORE
    try:
        credentials = await cli_auth.refresh_credentials(db, data.refresh_token)
    except cli_auth.CliAuthorizationError as exc:
        raise await _rejection(
            db,
            AUTH_CLI_REFRESH,
            exc,
            status_code=401,
            detail=INVALID_SESSION,
            target_type=None if exc.user_id is None else "user",
            target_id=exc.user_id,
        ) from exc
    await record_audit_event(
        db,
        AUTH_CLI_REFRESH,
        actor_user_id=credentials.user.id,
        target_type="user",
        target_id=credentials.user.id,
    )
    return credentials
