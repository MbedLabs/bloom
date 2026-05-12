import os
import uuid

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _random_prefix() -> str:
    seed = uuid.uuid4().int
    return "".join(_LETTERS[(seed >> (5 * i)) % 26] for i in range(3))


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
    suffix = uuid.uuid4().hex[:8]
    prefix = _random_prefix()
    create = api_client.post(
        "/api/projects",
        headers=headers,
        json={"name": f"Delete Me {suffix}", "prefix": prefix},
    )
    assert create.status_code == 201
    project_id = create.json()["id"]

    delete = api_client.delete(f"/api/projects/{project_id}", headers=headers)
    assert delete.status_code == 204

    missing = api_client.get(f"/api/projects/{project_id}", headers=headers)
    assert missing.status_code == 404


def test_admin_can_delete_project_with_requirements(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = uuid.uuid4().hex[:8]
    prefix = _random_prefix()
    create = api_client.post(
        "/api/projects",
        headers=headers,
        json={"name": f"Delete With Reqs {suffix}", "prefix": prefix},
    )
    assert create.status_code == 201
    project_id = create.json()["id"]

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
    suffix = uuid.uuid4().hex[:8]
    prefix = _random_prefix()
    create = api_client.post(
        "/api/projects",
        headers=headers,
        json={"name": f"Protected {suffix}", "prefix": prefix},
    )
    assert create.status_code == 201
    project_id = create.json()["id"]

    unauth = api_client.delete(f"/api/projects/{project_id}")
    assert unauth.status_code == 401
