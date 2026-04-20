import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from app.api import auth as auth_api
from app.api import users as users_api
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.services.token_service import TokenValidationError


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/forgot-password",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "scheme": "http",
            "http_version": "1.1",
        }
    )


@pytest.mark.asyncio
async def test_delete_user_cleans_known_user_references_before_delete():
    admin = User(
        id=1,
        email="admin@example.com",
        full_name="Admin",
        hashed_password=get_password_hash("adminpass"),
        role=UserRole.admin,
        is_active=True,
    )
    target_user = User(
        id=2,
        email="target@example.com",
        full_name="Target User",
        hashed_password=get_password_hash("targetpass"),
        role=UserRole.reviewer,
        is_active=True,
    )
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _ScalarResult(target_user),
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ]
        ),
        delete=AsyncMock(),
    )

    await users_api.delete_user(user_id=target_user.id, admin=admin, db=db)

    assert db.execute.await_count == 12
    stmt_texts = [str(call.args[0]) for call in db.execute.await_args_list]
    assert any("DELETE FROM user_tokens" in stmt for stmt in stmt_texts)
    assert any("UPDATE user_tokens" in stmt for stmt in stmt_texts)
    assert any("UPDATE users" in stmt for stmt in stmt_texts)
    assert any("UPDATE requirements" in stmt for stmt in stmt_texts)
    assert any("UPDATE test_cases" in stmt for stmt in stmt_texts)
    db.delete.assert_awaited_once_with(target_user)


@pytest.mark.asyncio
async def test_delete_user_rejects_admin_self_delete():
    admin = User(
        id=7,
        email="admin@example.com",
        full_name="Admin",
        hashed_password=get_password_hash("adminpass"),
        role=UserRole.admin,
        is_active=True,
    )
    db = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult(admin)), delete=AsyncMock())

    with pytest.raises(HTTPException) as exc:
        await users_api.delete_user(user_id=admin.id, admin=admin, db=db)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Admin users cannot delete their own account"
    assert db.execute.await_count == 1
    assert db.delete.await_count == 0


@pytest.mark.asyncio
async def test_delete_user_maps_integrity_errors_to_conflict_response():
    admin = User(
        id=1,
        email="admin@example.com",
        full_name="Admin",
        hashed_password=get_password_hash("adminpass"),
        role=UserRole.admin,
        is_active=True,
    )
    target_user = User(
        id=11,
        email="target@example.com",
        full_name="Target User",
        hashed_password=get_password_hash("targetpass"),
        role=UserRole.reviewer,
        is_active=True,
    )

    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _ScalarResult(target_user),
                IntegrityError("stmt", {}, Exception("fk failure")),
            ]
        ),
        delete=AsyncMock(),
    )

    with pytest.raises(HTTPException) as exc:
        await users_api.delete_user(user_id=target_user.id, admin=admin, db=db)

    assert exc.value.status_code == 409
    assert (
        exc.value.detail
        == "User could not be deleted because related records still reference this account"
    )
    assert db.delete.await_count == 0


@pytest.mark.asyncio
async def test_forgot_password_existing_user_returns_generic_message_and_sends_email(monkeypatch):
    user = User(
        id=3,
        email="reviewer@example.com",
        full_name="Reviewer",
        hashed_password=get_password_hash("reviewerpass"),
        role=UserRole.reviewer,
        is_active=True,
    )
    db = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult(user)), flush=AsyncMock())

    create_token = AsyncMock(return_value="reset-token")
    send_email = MagicMock()
    monkeypatch.setattr(auth_api, "create_user_token", create_token)
    monkeypatch.setattr(auth_api, "send_password_reset_email", send_email)

    response = await auth_api.forgot_password(
        request=_request(),
        data=ForgotPasswordRequest(email=user.email),
        db=db,
    )

    assert response.message == "If the account exists, a password reset email has been sent"
    create_token.assert_awaited_once()
    send_email.assert_called_once()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_forgot_password_unknown_user_still_returns_generic_message(monkeypatch):
    db = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult(None)), flush=AsyncMock())

    create_token = AsyncMock(return_value="reset-token")
    send_email = MagicMock()
    monkeypatch.setattr(auth_api, "create_user_token", create_token)
    monkeypatch.setattr(auth_api, "send_password_reset_email", send_email)

    response = await auth_api.forgot_password(
        request=_request(),
        data=ForgotPasswordRequest(email="missing@example.com"),
        db=db,
    )

    assert response.message == "If the account exists, a password reset email has been sent"
    assert create_token.await_count == 0
    assert send_email.call_count == 0
    assert db.flush.await_count == 0


@pytest.mark.asyncio
async def test_reset_password_updates_user_hash_and_marks_token_used(monkeypatch):
    user = User(
        id=5,
        email="dev@example.com",
        full_name="Developer",
        hashed_password=get_password_hash("old-password"),
        role=UserRole.maintainer,
        is_active=True,
    )
    user_token = SimpleNamespace(user_id=user.id)

    get_valid = AsyncMock(return_value=user_token)
    mark_used = AsyncMock()
    monkeypatch.setattr(auth_api, "get_valid_token", get_valid)
    monkeypatch.setattr(auth_api, "mark_token_used", mark_used)

    db = SimpleNamespace(get=AsyncMock(return_value=user), flush=AsyncMock())

    response = await auth_api.reset_password(
        data=ResetPasswordRequest(token="valid-token", new_password="new-password-123"),
        db=db,
    )

    assert response.message == "Password reset successfully"
    assert verify_password("new-password-123", user.hashed_password)
    assert user.password_set_at is not None
    mark_used.assert_awaited_once_with(db, user_token)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "detail",
    ["Invalid token", "Token has expired", "Token has already been used"],
)
async def test_reset_password_rejects_invalid_expired_or_used_tokens(detail, monkeypatch):
    get_valid = AsyncMock(side_effect=TokenValidationError(detail))
    monkeypatch.setattr(auth_api, "get_valid_token", get_valid)

    db = SimpleNamespace(get=AsyncMock(), flush=AsyncMock())

    with pytest.raises(HTTPException) as exc:
        await auth_api.reset_password(
            data=ResetPasswordRequest(token="bad-token", new_password="new-password-123"),
            db=db,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == detail
    assert db.get.await_count == 0
    assert db.flush.await_count == 0
