"""HTTP tests for requirements CRUD (TST-001)."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_project(client: TestClient, headers: dict[str, str]) -> dict:
    resp = client.post(
        "/api/projects",
        json={"name": "Req Test Project", "prefix": "RTP", "description": "test"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_requirements_crud_roundtrip(api_client: TestClient):
    headers = _auth_headers(api_client)
    project = _create_project(api_client, headers)
    pid = project["id"]

    empty = api_client.get("/api/requirements", params={"project_id": pid}, headers=headers)
    assert empty.status_code == 200
    assert empty.json()["items"] == []

    created = api_client.post(
        "/api/requirements",
        json={"project_id": pid, "title": "System shall boot"},
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "System shall boot"
    assert body["req_id"].startswith("RTP-REQ-")

    listed = api_client.get("/api/requirements", params={"project_id": pid}, headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1

    got = api_client.get(f"/api/requirements/{body['id']}", headers=headers)
    assert got.status_code == 200
    assert got.json()["req_id"] == body["req_id"]

    updated = api_client.patch(
        f"/api/requirements/{body['id']}",
        json={"title": "Updated title"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated title"

    deleted = api_client.delete(f"/api/requirements/{body['id']}", headers=headers)
    assert deleted.status_code in (200, 204)
