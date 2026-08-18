"""Verified email-change flow and invitation-as-verification (real PostgreSQL)."""

import asyncio
import os
import re

import asyncpg
from fastapi.testclient import TestClient

from tests.conftest import unique_email, unique_name, unique_prefix

COOKIE = "bloom_refresh_token"


def _bearer(access: str) -> dict:
    return {"Authorization": f"Bearer {access}"}


def _admin_access(api_client) -> str:
    from app.core.config import settings

    api_client.cookies.clear()
    resp = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _create_user(api_client, admin_access, email, password, role="external"):
    resp = api_client.post(
        "/api/users",
        json={"email": email, "full_name": "Mover", "password": password, "role": role},
        headers=_bearer(admin_access),
    )
    assert resp.status_code == 201, resp.text


def _login(api_client, email, password):
    api_client.cookies.clear()
    return api_client.post("/api/auth/login", json={"email": email, "password": password})


def _replace_pending_email_directly(user_id: int, pending_email: str) -> None:
    """Recreate the stale-approval race outcome without timing-dependent sleeps."""

    async def update_pending_email() -> None:
        database_url = (os.environ.get("DATABASE_URL") or os.environ["BLOOM_DATABASE_URL"]).replace(
            "postgresql+asyncpg://", "postgresql://", 1
        )
        connection = await asyncpg.connect(database_url)
        try:
            await connection.execute(
                "UPDATE users SET pending_email = $1 WHERE id = $2",
                pending_email,
                user_id,
            )
        finally:
            await connection.close()

    asyncio.run(update_pending_email())


def test_admin_self_change_authorizes_current_then_verifies_new_mailbox(
    api_client: TestClient,
):
    import app.api.auth as auth_module

    seeded_admin_access = _admin_access(api_client)
    old_email = unique_email("self-admin-old")
    new_email = unique_email("self-admin-new")
    password = "Self-Admin-Password-123"
    _create_user(api_client, seeded_admin_access, old_email, password, role="admin")

    login = _login(api_client, old_email, password)
    assert login.status_code == 200, login.text
    access = login.json()["access_token"]
    refresh = api_client.cookies.get(COOKIE)

    current_mail: list[dict[str, str]] = []
    new_mail: list[dict[str, str]] = []
    original_authorization = getattr(auth_module, "send_email_change_authorization_email", None)
    original_verification = getattr(auth_module, "send_email_change_email", None)
    auth_module.send_email_change_authorization_email = lambda **kw: current_mail.append(kw)
    auth_module.send_email_change_email = lambda **kw: new_mail.append(kw)
    try:
        requested = api_client.post(
            "/api/auth/me/email",
            json={"current_password": password, "new_email": new_email},
            headers=_bearer(access),
        )
        assert requested.status_code == 200, requested.text
        assert "current email" in requested.json()["message"].lower()

        pending_current = api_client.get("/api/auth/me", headers=_bearer(access))
        assert pending_current.json()["email"] == old_email
        assert pending_current.json()["pending_email"] == new_email
        assert pending_current.json()["email_change_status"] == "awaiting_current_confirmation"
        assert len(current_mail) == 1
        assert current_mail[0]["to_email"] == old_email
        assert new_mail == []

        current_token = re.search(r"token=([^&\s]+)", current_mail[0]["confirm_link"])
        assert current_token
        authorized = api_client.post(
            "/api/auth/confirm-email-change",
            json={"token": current_token.group(1)},
        )
        assert authorized.status_code == 200, authorized.text
        assert "new email" in authorized.json()["message"].lower()

        pending_new = api_client.get("/api/auth/me", headers=_bearer(access))
        assert pending_new.status_code == 200
        assert pending_new.json()["email"] == old_email
        assert pending_new.json()["email_change_status"] == "awaiting_confirmation"
        assert len(new_mail) == 1
        assert new_mail[0]["to_email"] == new_email

        new_token = re.search(r"token=([^&\s]+)", new_mail[0]["confirm_link"])
        assert new_token
        confirmed = api_client.post(
            "/api/auth/confirm-email-change",
            json={"token": new_token.group(1)},
        )
        assert confirmed.status_code == 200, confirmed.text
    finally:
        if original_authorization is None:
            delattr(auth_module, "send_email_change_authorization_email")
        else:
            auth_module.send_email_change_authorization_email = original_authorization
        if original_verification is None:
            delattr(auth_module, "send_email_change_email")
        else:
            auth_module.send_email_change_email = original_verification

    assert api_client.get("/api/auth/me", headers=_bearer(access)).status_code == 401
    api_client.cookies.clear()
    assert api_client.post("/api/auth/refresh", cookies={COOKIE: refresh}).status_code == 401
    assert _login(api_client, old_email, password).status_code == 401
    assert _login(api_client, new_email, password).status_code == 200


def test_email_change_requires_confirmation_and_ends_sessions(api_client: TestClient):
    admin_access = _admin_access(api_client)
    old_email = unique_email("mover-old")
    new_email = unique_email("mover-new")
    password = "Mover-Password-123"
    _create_user(api_client, admin_access, old_email, password)

    login1 = _login(api_client, old_email, password)
    assert login1.status_code == 200, login1.text
    access1 = login1.json()["access_token"]
    refresh1 = api_client.cookies.get(COOKIE)

    import app.api.users as users_module

    captured: dict[str, str] = {}
    original = users_module.send_email_change_email
    users_module.send_email_change_email = lambda **kw: captured.update(
        link=kw["confirm_link"],
        old_email=kw["old_email"],
        new_email=kw["new_email"],
    )
    try:
        req = api_client.post(
            "/api/auth/me/email",
            json={"current_password": password, "new_email": new_email},
            headers=_bearer(access1),
        )
        assert req.status_code == 200, req.text
        assert captured == {}

        pending = api_client.get("/api/auth/me", headers=_bearer(access1))
        assert pending.json()["email_change_status"] == "requested"
        approve = api_client.post(
            f"/api/users/{pending.json()['id']}/email/approve",
            headers=_bearer(admin_access),
        )
        assert approve.status_code == 200, approve.text
    finally:
        users_module.send_email_change_email = original

    # Approved but unconfirmed: login email is unchanged, and the new mailbox
    # receives an email naming both addresses.
    me = api_client.get("/api/auth/me", headers=_bearer(access1))
    assert me.status_code == 200
    assert me.json()["email"] == old_email
    assert me.json()["pending_email"] == new_email
    assert me.json()["email_change_status"] == "awaiting_confirmation"
    assert captured["old_email"] == old_email
    assert captured["new_email"] == new_email
    assert _login(api_client, new_email, password).status_code == 401
    assert _login(api_client, old_email, password).status_code == 200

    match = re.search(r"token=([^&\s]+)", captured["link"])
    assert match, captured
    confirm = api_client.post("/api/auth/confirm-email-change", json={"token": match.group(1)})
    assert confirm.status_code == 200, confirm.text

    # Confirmed: pre-change tokens dead, old address cannot log in, new can, verified.
    assert api_client.get("/api/auth/me", headers=_bearer(access1)).status_code == 401
    api_client.cookies.clear()
    assert api_client.post("/api/auth/refresh", cookies={COOKIE: refresh1}).status_code == 401
    assert _login(api_client, old_email, password).status_code == 401
    after = _login(api_client, new_email, password)
    assert after.status_code == 200, after.text
    me2 = api_client.get("/api/auth/me", headers=_bearer(after.json()["access_token"]))
    assert me2.json()["email"] == new_email
    assert me2.json()["pending_email"] is None
    assert me2.json()["email_change_status"] is None
    assert me2.json()["email_verified_at"] is not None


def test_confirmation_token_cannot_apply_a_different_pending_email(
    api_client: TestClient,
):
    import app.api.users as users_module

    admin_access = _admin_access(api_client)
    old_email = unique_email("race-old")
    approved_email = unique_email("race-approved")
    unapproved_email = unique_email("race-unapproved")
    password = "Race-Password-123"
    _create_user(api_client, admin_access, old_email, password)

    login = _login(api_client, old_email, password)
    user_access = login.json()["access_token"]
    pending = api_client.post(
        "/api/auth/me/email",
        json={"current_password": password, "new_email": approved_email},
        headers=_bearer(user_access),
    )
    assert pending.status_code == 200, pending.text
    user_id = api_client.get("/api/auth/me", headers=_bearer(user_access)).json()["id"]

    captured: dict[str, str] = {}
    original = users_module.send_email_change_email
    users_module.send_email_change_email = lambda **kw: captured.update(link=kw["confirm_link"])
    try:
        approved = api_client.post(
            f"/api/users/{user_id}/email/approve",
            headers=_bearer(admin_access),
        )
        assert approved.status_code == 200, approved.text
    finally:
        users_module.send_email_change_email = original

    token = re.search(r"token=([^&\s]+)", captured["link"]).group(1)
    _replace_pending_email_directly(user_id, unapproved_email)

    confirmed = api_client.post("/api/auth/confirm-email-change", json={"token": token})
    assert confirmed.status_code == 400, confirmed.text
    assert _login(api_client, old_email, password).status_code == 200
    assert _login(api_client, approved_email, password).status_code == 401
    assert _login(api_client, unapproved_email, password).status_code == 401


def test_wrong_current_password_does_not_start_email_change(api_client: TestClient):
    admin_access = _admin_access(api_client)
    email = unique_email("mover-guard")
    password = "Mover-Guard-123"
    _create_user(api_client, admin_access, email, password)
    login = _login(api_client, email, password)
    access = login.json()["access_token"]

    resp = api_client.post(
        "/api/auth/me/email",
        json={"current_password": "wrong-password-xx", "new_email": unique_email("guard-new")},
        headers=_bearer(access),
    )
    assert resp.status_code == 400
    assert api_client.get("/api/auth/me", headers=_bearer(access)).json()["pending_email"] is None


def test_admin_email_change_uses_confirmation_and_generic_update_cannot_bypass(
    api_client: TestClient,
):
    import app.api.users as users_module

    admin_access = _admin_access(api_client)
    old_email = unique_email("admin-flow-old")
    new_email = unique_email("admin-flow-new")
    password = "Admin-Flow-Password-123"
    _create_user(api_client, admin_access, old_email, password)
    user = next(
        item
        for item in api_client.get("/api/users", headers=_bearer(admin_access)).json()
        if item["email"] == old_email
    )

    bypass = api_client.patch(
        f"/api/users/{user['id']}",
        json={"email": new_email},
        headers=_bearer(admin_access),
    )
    assert bypass.status_code == 422

    captured: dict[str, str] = {}
    original = users_module.send_email_change_email
    users_module.send_email_change_email = lambda **kw: captured.update(link=kw["confirm_link"])
    try:
        started = api_client.post(
            f"/api/users/{user['id']}/email",
            json={"new_email": new_email},
            headers=_bearer(admin_access),
        )
        assert started.status_code == 200, started.text
        assert started.json()["email"] == old_email
        assert started.json()["email_change_status"] == "awaiting_confirmation"
    finally:
        users_module.send_email_change_email = original

    token = re.search(r"token=([^&\s]+)", captured["link"]).group(1)
    confirmed = api_client.post("/api/auth/confirm-email-change", json={"token": token})
    assert confirmed.status_code == 200, confirmed.text
    assert _login(api_client, old_email, password).status_code == 401
    assert _login(api_client, new_email, password).status_code == 200


def test_accepting_invitation_verifies_the_account(api_client: TestClient):
    import app.api.users as users_module

    admin_access = _admin_access(api_client)
    email = unique_email("invited-verified")

    captured: dict[str, str] = {}
    original = users_module.send_invite_email
    users_module.send_invite_email = lambda **kw: captured.update(link=kw["invite_link"])
    try:
        resp = api_client.post(
            "/api/users/invite",
            json={"email": email, "full_name": "Invited", "role": "external"},
            headers=_bearer(admin_access),
        )
        assert resp.status_code == 201, resp.text
    finally:
        users_module.send_invite_email = original

    token = re.search(r"token=([^&\s]+)", captured["link"]).group(1)
    accept = api_client.post(
        "/api/auth/accept-invite", json={"token": token, "password": "Invited-Password-123"}
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["requires_email_verification"] is False

    login = _login(api_client, email, "Invited-Password-123")
    assert login.status_code == 200
    me = api_client.get("/api/auth/me", headers=_bearer(login.json()["access_token"]))
    assert me.json()["email_verified_at"] is not None
