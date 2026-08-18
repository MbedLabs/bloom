"""HTTP create flows assign public IDs without client-supplied identifiers."""

import os
import re

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest
from fastapi.testclient import TestClient

from app.core.id_generator import DOC_ID_PATTERN
from tests.conftest import create_project


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


@pytest.fixture
def project(api_client: TestClient, auth_headers: dict[str, str]) -> dict:
    return create_project(api_client, auth_headers, "Create ID Project")


@pytest.fixture
def project_prefix(project: dict) -> str:
    return project["prefix"]


@pytest.fixture
def project_id(project: dict) -> int:
    return project["id"]


@pytest.mark.parametrize(
    ("path", "payload", "id_field", "type_code"),
    [
        (
            "/api/requirements",
            {"title": "Requirement"},
            "req_id",
            "REQ",
        ),
        (
            "/api/test-cases",
            {"title": "Test case"},
            "tc_id",
            "TC",
        ),
        (
            "/api/projects/{project_id}/documents",
            {"title": "Specification", "doc_type": "SPEC"},
            "doc_id",
            "SPEC",
        ),
    ],
)
def test_create_assigns_public_id_without_client_field(
    api_client: TestClient,
    auth_headers: dict[str, str],
    project_id: int,
    project_prefix: str,
    path: str,
    payload: dict[str, str],
    id_field: str,
    type_code: str,
):
    body = {"project_id": project_id, **payload}
    resolved_path = path.format(project_id=project_id)
    response = api_client.post(resolved_path, headers=auth_headers, json=body)
    assert response.status_code == 201, response.text
    data = response.json()
    public_id = data[id_field]
    assert DOC_ID_PATTERN.fullmatch(public_id)
    assert public_id.startswith(f"{project_prefix}-{type_code}-")
    assert re.fullmatch(
        re.escape(project_prefix) + "-" + re.escape(type_code) + r"-\d{3}",
        public_id,
    )
