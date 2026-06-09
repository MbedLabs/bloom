import os
import uuid

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient


def _login_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _admin_headers(client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    return _login_headers(client, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)


def _create_project(client: TestClient, headers: dict[str, str], name: str, prefix: str) -> dict:
    resp = client.post(
        "/api/projects",
        json={"name": name, "prefix": prefix, "description": "IAM regression"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_user(
    client: TestClient,
    headers: dict[str, str],
    *,
    email: str,
    password: str,
    role: str = "maintainer",
) -> dict:
    resp = client.post(
        "/api/users",
        headers=headers,
        json={
            "email": email,
            "full_name": "Scoped User",
            "password": password,
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _add_membership(
    client: TestClient,
    headers: dict[str, str],
    *,
    project_id: int,
    user_id: int,
    role: str = "maintainer",
) -> dict:
    resp = client.post(
        f"/api/projects/{project_id}/members",
        headers=headers,
        json={"user_id": user_id, "role": role},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_unassigned_maintainer_cannot_access_other_project_data(api_client: TestClient):
    admin_headers = _admin_headers(api_client)
    suffix = uuid.uuid4().hex[:8]

    allowed = _create_project(
        api_client, admin_headers, f"Allowed {suffix}", f"A{suffix[:2].upper()}"
    )
    blocked = _create_project(
        api_client, admin_headers, f"Blocked {suffix}", f"B{suffix[:2].upper()}"
    )

    created_requirement = api_client.post(
        "/api/requirements",
        headers=admin_headers,
        json={"project_id": blocked["id"], "title": f"Blocked requirement {suffix}"},
    )
    assert created_requirement.status_code == 201, created_requirement.text
    requirement_id = created_requirement.json()["id"]

    user_password = "maintainer-password-123"
    user = _create_user(
        api_client,
        admin_headers,
        email=f"maintainer-{suffix}@example.com",
        password=user_password,
    )
    _add_membership(
        api_client,
        admin_headers,
        project_id=allowed["id"],
        user_id=user["id"],
    )

    maintainer_headers = _login_headers(api_client, user["email"], user_password)

    projects = api_client.get("/api/projects", headers=maintainer_headers)
    assert projects.status_code == 200
    project_ids = {project["id"] for project in projects.json()}
    assert project_ids == {allowed["id"]}

    blocked_list = api_client.get(
        "/api/requirements",
        params={"project_id": blocked["id"]},
        headers=maintainer_headers,
    )
    assert blocked_list.status_code == 403

    blocked_get = api_client.get(
        f"/api/requirements/{requirement_id}",
        headers=maintainer_headers,
    )
    assert blocked_get.status_code == 403

    blocked_traceability = api_client.get(
        f"/api/traceability/coverage-gaps/{blocked['id']}",
        headers=maintainer_headers,
    )
    assert blocked_traceability.status_code == 403

    dashboard = api_client.get("/api/dashboard/stats", headers=maintainer_headers)
    assert dashboard.status_code == 200
    dashboard_project_ids = {project["id"] for project in dashboard.json()["projects"]}
    assert blocked["id"] not in dashboard_project_ids

    blocked_import = api_client.post(
        f"/api/projects/{allowed['id']}/import",
        headers=maintainer_headers,
        json={
            "source_project_id": blocked["id"],
            "doc_type": "REQ",
            "doc_ids": [requirement_id],
            "include_links": True,
        },
    )
    assert blocked_import.status_code == 403
