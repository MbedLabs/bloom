"""Verified email-change flow and invitation-as-verification (real PostgreSQL)."""

import re

from fastapi.testclient import TestClient

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


def test_email_change_requires_confirmation_and_ends_sessions(api_client: TestClient):
    import app.api.auth as auth_module

    admin_access = _admin_access(api_client)
    old_email = "mover-old@example.com"
    new_email = "mover-new@example.com"
    password = "Mover-Password-123"
    _create_user(api_client, admin_access, old_email, password)

    login1 = _login(api_client, old_email, password)
    assert login1.status_code == 200, login1.text
    access1 = login1.json()["access_token"]
    refresh1 = api_client.cookies.get(COOKIE)

    captured: dict[str, str] = {}
    original = auth_module.send_email_change_email
    auth_module.send_email_change_email = lambda **kw: captured.update(link=kw["confirm_link"])
    try:
        req = api_client.post(
            "/api/auth/me/email",
            json={"current_password": password, "new_email": new_email},
            headers=_bearer(access1),
        )
        assert req.status_code == 200, req.text
    finally:
        auth_module.send_email_change_email = original

    # Unconfirmed: login email is unchanged, and the pending address is recorded.
    me = api_client.get("/api/auth/me", headers=_bearer(access1))
    assert me.status_code == 200
    assert me.json()["email"] == old_email
    assert me.json()["pending_email"] == new_email
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
    assert me2.json()["email_verified_at"] is not None


def test_wrong_current_password_does_not_start_email_change(api_client: TestClient):
    admin_access = _admin_access(api_client)
    email = "mover-guard@example.com"
    password = "Mover-Guard-123"
    _create_user(api_client, admin_access, email, password)
    login = _login(api_client, email, password)
    access = login.json()["access_token"]

    resp = api_client.post(
        "/api/auth/me/email",
        json={"current_password": "wrong-password-xx", "new_email": "guard-new@example.com"},
        headers=_bearer(access),
    )
    assert resp.status_code == 400
    assert api_client.get("/api/auth/me", headers=_bearer(access)).json()["pending_email"] is None


def test_accepting_invitation_verifies_the_account(api_client: TestClient):
    import app.api.users as users_module

    admin_access = _admin_access(api_client)
    email = "invited-verified@example.com"

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
