"""Refresh-token flow against real PostgreSQL.

Exercises the httpOnly cookie, single-use rotation, and server-side revocation
end to end (real login, real DB-backed user_tokens rows).
"""

from fastapi.testclient import TestClient

COOKIE = "bloom_refresh_token"


def _login(api_client: TestClient):
    from app.core.config import settings

    api_client.cookies.clear()
    resp = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    return resp


def test_login_sets_httponly_refresh_cookie(api_client: TestClient):
    resp = _login(api_client)
    set_cookie = resp.headers.get("set-cookie", "")
    assert COOKIE in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/api/auth" in set_cookie
    assert api_client.cookies.get(COOKIE)


def test_refresh_issues_a_working_access_token(api_client: TestClient):
    from app.core.config import settings

    _login(api_client)
    resp = api_client.post("/api/auth/refresh")
    assert resp.status_code == 200, resp.text
    new_access = resp.json()["access_token"]
    me = api_client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200
    assert me.json()["email"] == settings.ADMIN_EMAIL


def test_refresh_without_cookie_is_rejected(api_client: TestClient):
    api_client.cookies.clear()
    assert api_client.post("/api/auth/refresh").status_code == 401


def test_refresh_rotates_and_replayed_old_token_is_rejected(api_client: TestClient):
    _login(api_client)
    old_value = api_client.cookies.get(COOKIE)

    first = api_client.post("/api/auth/refresh")  # rotates: jar now holds a new token
    assert first.status_code == 200
    new_value = api_client.cookies.get(COOKIE)
    assert new_value and new_value != old_value

    api_client.cookies.clear()
    replay = api_client.post("/api/auth/refresh", cookies={COOKIE: old_value})
    assert replay.status_code == 401


def test_logout_revokes_refresh_token(api_client: TestClient):
    _login(api_client)
    assert api_client.post("/api/auth/logout").status_code == 200
    assert api_client.post("/api/auth/refresh").status_code == 401
