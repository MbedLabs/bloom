"""HTTP coverage for typed link rule enforcement."""

import os
import secrets
import string

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(api_client: TestClient):
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_link_rejects_forbidden_role_pair(
    api_client: TestClient,
    auth_headers: dict[str, str],
):
    project_prefix = "".join(secrets.choice(string.ascii_uppercase) for _ in range(3))
    project = api_client.post(
        "/api/projects",
        headers=auth_headers,
        json={"name": f"Link Rules Project {project_prefix}", "prefix": project_prefix},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    requirement = api_client.post(
        "/api/requirements",
        headers=auth_headers,
        json={"project_id": project_id, "title": "Requirement"},
    )
    assert requirement.status_code == 201
    requirement_id = requirement.json()["id"]

    test_case = api_client.post(
        "/api/test-cases",
        headers=auth_headers,
        json={"project_id": project_id, "title": "Test case"},
    )
    assert test_case.status_code == 201
    test_case_id = test_case.json()["id"]

    response = api_client.post(
        "/api/links",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "source_type": "TC",
            "source_id": test_case_id,
            "target_type": "REQ",
            "target_id": requirement_id,
            "role": "references",
        },
    )
    assert response.status_code == 422
    assert "not allowed" in response.json()["detail"].lower()
