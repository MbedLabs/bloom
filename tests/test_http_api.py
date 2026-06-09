"""
HTTP-level pytest coverage using FastAPI ``TestClient`` (lifespan runs: DB tables, migrations, admin seed).

**Local:** omit ``BLOOM_DOTENV_DISABLED``; ``tests/conftest.py`` loads monorepo ``../.env`` so ``BLOOM_DATABASE_URL``
/ ``BLOOM_SECRET_KEY`` apply (unless already set in the shell).

**CI:** pass ``DATABASE_URL``, ``SECRET_KEY``, and ``BLOOM_DOTENV_DISABLED=1`` so the job Postgres wins
(see ``Settings.settings_customise_sources``).

Requires a reachable Postgres matching the effective ``DATABASE_URL``.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient


def test_health_and_root(api_client: TestClient):
    h = api_client.get("/api/health")
    assert h.status_code == 200
    payload = h.json()
    assert payload.get("status") == "healthy"
    assert "version" in payload

    r = api_client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "Bloom" in str(body.get("message", ""))
    assert "version" in body


def test_docs_disabled_openapi_returns_404(api_client: TestClient):
    docs = api_client.get("/api/openapi.json")
    assert docs.status_code == 404


def test_login_rejects_wrong_password(api_client: TestClient):
    resp = api_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "not-the-admin-password-xxxxx"},
    )
    assert resp.status_code == 401


def test_projects_and_links_require_auth(api_client: TestClient):
    p = api_client.get("/api/projects")
    assert p.status_code == 401

    links = api_client.get("/api/links", params={"project_id": 1})
    assert links.status_code == 401


def test_login_me_and_projects_roundtrip(api_client: TestClient):
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = api_client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == settings.ADMIN_EMAIL

    projects = api_client.get("/api/projects", headers=headers)
    assert projects.status_code == 200
    assert isinstance(projects.json(), list)

    links_empty = api_client.get("/api/links", headers=headers, params={"project_id": 999999999})
    assert links_empty.status_code == 404
