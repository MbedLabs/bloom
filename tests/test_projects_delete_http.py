import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

from tests.conftest import create_project, unique_suffix


def _admin_headers(api_client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_delete_project(api_client: TestClient):
    headers = _admin_headers(api_client)
    project_id = create_project(api_client, headers, "Delete Me")["id"]

    delete = api_client.delete(f"/api/projects/{project_id}", headers=headers)
    assert delete.status_code == 204

    missing = api_client.get(f"/api/projects/{project_id}", headers=headers)
    assert missing.status_code == 404


def test_admin_can_delete_project_with_requirements(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, "Delete With Reqs")["id"]

    requirement = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": f"Req {suffix}"},
    )
    assert requirement.status_code == 201

    delete = api_client.delete(f"/api/projects/{project_id}", headers=headers)
    assert delete.status_code == 204

    missing = api_client.get(f"/api/projects/{project_id}", headers=headers)
    assert missing.status_code == 404


def test_delete_project_requires_admin(api_client: TestClient):
    headers = _admin_headers(api_client)
    project_id = create_project(api_client, headers, "Protected")["id"]

    unauth = api_client.delete(f"/api/projects/{project_id}")
    assert unauth.status_code == 401
