"""HTTP tests for requirements CRUD (TST-001)."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

from tests.conftest import create_project


def _auth_headers(client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_requirements_crud_roundtrip(api_client: TestClient):
    headers = _auth_headers(api_client)
    project = create_project(api_client, headers, "Req Test Project", description="test")
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
    assert body["req_id"].startswith(f"{project['prefix']}-REQ-")

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


BODY = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "boots in "}, {"type": "mention", "attrs": {"id": "1", "label": "BOOT_BUDGET_MS", "mentionSuggestionChar": "{{"}}]}]}


def test_requirement_body_is_returned(api_client: TestClient):
    """The editor body a requirement was created with comes back on create, list, detail and update."""
    headers = _auth_headers(api_client)
    pid = create_project(api_client, headers, "Req Body Project", description="test")["id"]
    created = api_client.post("/api/requirements", json={"project_id": pid, "title": "Boots in budget", "content_json": BODY, "content_html": "<p>boots in {{BOOT_BUDGET_MS}}</p>"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["content_json"] == BODY
    assert created.json()["content_html"] == "<p>boots in {{BOOT_BUDGET_MS}}</p>"
    rid = created.json()["id"]
    assert api_client.get("/api/requirements", params={"project_id": pid}, headers=headers).json()["items"][0]["content_json"] == BODY
    assert api_client.get(f"/api/requirements/{rid}", headers=headers).json()["content_json"] == BODY
    updated = api_client.patch(f"/api/requirements/{rid}", json={"title": "Boots"}, headers=headers)
    assert updated.json()["content_json"] == BODY


def test_test_case_body_is_returned(api_client: TestClient):
    """The editor body a test case was created with comes back on create, list and detail."""
    headers = _auth_headers(api_client)
    pid = create_project(api_client, headers, "TC Body Project", description="test")["id"]
    created = api_client.post("/api/test-cases", json={"project_id": pid, "title": "Boot time", "content_json": BODY, "content_html": "<p>boots in {{BOOT_BUDGET_MS}}</p>"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["content_json"] == BODY
    tid = created.json()["id"]
    assert api_client.get("/api/test-cases", params={"project_id": pid}, headers=headers).json()["items"][0]["content_json"] == BODY
    assert api_client.get(f"/api/test-cases/{tid}", headers=headers).json()["content_html"] == "<p>boots in {{BOOT_BUDGET_MS}}</p>"
