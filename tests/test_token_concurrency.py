"""One-time tokens survive concurrent use exactly once (real PostgreSQL).

Fires several simultaneous requests at a single token and asserts exactly one
succeeds. The atomic ``UPDATE ... RETURNING`` claim is what makes this hold:
without it, read-then-update would let multiple racers pass the check together.
"""

import re
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

COOKIE = "bloom_refresh_token"
N = 6


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


def _create_user(api_client, admin_access, email, password):
    resp = api_client.post(
        "/api/users",
        json={"email": email, "full_name": "Racer", "password": password, "role": "external"},
        headers=_bearer(admin_access),
    )
    assert resp.status_code == 201, resp.text


def _fire(make_request):
    with ThreadPoolExecutor(max_workers=N) as pool:
        return [f.result() for f in [pool.submit(make_request) for _ in range(N)]]


def _extract_token(link: str) -> str:
    match = re.search(r"token=([^&\s]+)", link)
    assert match, f"no token in link: {link!r}"
    return match.group(1)


def test_concurrent_refresh_yields_one_success(api_client: TestClient):
    from app.core.config import settings

    api_client.cookies.clear()
    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    old_cookie = api_client.cookies.get(COOKIE)
    api_client.cookies.clear()

    codes = _fire(
        lambda: api_client.post("/api/auth/refresh", cookies={COOKIE: old_cookie}).status_code
    )
    assert codes.count(200) == 1, codes
    assert all(c in (200, 401) for c in codes), codes


def test_concurrent_password_reset_yields_one_success(api_client: TestClient):
    import app.api.auth as auth_module

    admin_access = _admin_access(api_client)
    email = "reset-racer@example.com"
    _create_user(api_client, admin_access, email, "Reset-Racer-123")

    captured: dict[str, str] = {}
    original = auth_module.send_password_reset_email
    auth_module.send_password_reset_email = lambda **kw: captured.update(link=kw["reset_link"])
    try:
        assert (
            api_client.post("/api/auth/forgot-password", json={"email": email}).status_code == 200
        )
    finally:
        auth_module.send_password_reset_email = original
    token = _extract_token(captured["link"])

    codes = _fire(
        lambda: api_client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "Fresh-Reset-456"},
        ).status_code
    )
    assert codes.count(200) == 1, codes
    assert all(c in (200, 400) for c in codes), codes


def test_concurrent_accept_invite_yields_one_success(api_client: TestClient):
    import app.api.users as users_module

    admin_access = _admin_access(api_client)
    email = "invite-racer@example.com"

    captured: dict[str, str] = {}
    original = users_module.send_invite_email
    users_module.send_invite_email = lambda **kw: captured.update(link=kw["invite_link"])
    try:
        resp = api_client.post(
            "/api/users/invite",
            json={"email": email, "full_name": "Invite Racer", "role": "external"},
            headers=_bearer(admin_access),
        )
        assert resp.status_code == 201, resp.text
    finally:
        users_module.send_invite_email = original
    token = _extract_token(captured["link"])

    codes = _fire(
        lambda: api_client.post(
            "/api/auth/accept-invite",
            json={"token": token, "password": "Invite-Racer-789"},
        ).status_code
    )
    assert codes.count(200) == 1, codes
    assert all(c in (200, 400) for c in codes), codes


def test_concurrent_email_verification_yields_one_success(api_client: TestClient):
    import app.api.auth as auth_module

    admin_access = _admin_access(api_client)
    email = "verify-racer@example.com"
    password = "Verify-Racer-123"
    _create_user(api_client, admin_access, email, password)

    api_client.cookies.clear()
    login = api_client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    access = login.json()["access_token"]

    captured: dict[str, str] = {}
    original = auth_module.send_verification_email
    auth_module.send_verification_email = lambda **kw: captured.update(link=kw["verification_link"])
    try:
        resp = api_client.post("/api/auth/resend-verification", headers=_bearer(access))
        assert resp.status_code == 200, resp.text
    finally:
        auth_module.send_verification_email = original
    token = _extract_token(captured["link"])

    codes = _fire(
        lambda: api_client.post("/api/auth/verify-email", json={"token": token}).status_code
    )
    assert codes.count(200) == 1, codes
    assert all(c in (200, 400) for c in codes), codes
