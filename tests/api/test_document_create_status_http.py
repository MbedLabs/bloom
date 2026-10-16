"""HTTP document create accepts the first status the create page sends."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest
from fastapi.testclient import TestClient

from tests.conftest import create_project


@pytest.fixture
def auth_headers(api_client: TestClient):
    """Bearer headers for the seeded administrator."""
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def project_id(api_client: TestClient, auth_headers: dict[str, str]) -> int:
    """A fresh project for the document creates."""
    return create_project(api_client, auth_headers, "Document Status Project")["id"]


@pytest.mark.parametrize("doc_type", ["SPEC", "PRT", "RPT", "STD"])
def test_create_with_the_body_the_create_page_sends(
    api_client: TestClient, auth_headers: dict[str, str], project_id: int, doc_type: str
):
    """The create page body, status included, creates the document in that status."""
    response = api_client.post(
        f"/api/projects/{project_id}/documents",
        json={
            "project_id": project_id,
            "title": f"{doc_type} from the create page",
            "doc_type": doc_type,
            "description": "Created as the create page does",
            "content_json": None,
            "status": "Draft",
            "visibility": "internal",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["doc_type"] == doc_type
    assert body["status"] == "Draft"


def test_create_without_status_is_draft(
    api_client: TestClient, auth_headers: dict[str, str], project_id: int
):
    """A create that names no status still gives a Draft document."""
    response = api_client.post(
        f"/api/projects/{project_id}/documents",
        json={"project_id": project_id, "title": "Specification", "doc_type": "SPEC"},
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "Draft"


@pytest.mark.parametrize("status", ["Review", "Approved", "Rejected", "Obsolete"])
def test_create_naming_another_first_status_is_refused(
    api_client: TestClient, auth_headers: dict[str, str], project_id: int, status: str
):
    """A create naming a first status other than Draft answers 422 and creates nothing."""
    response = api_client.post(
        f"/api/projects/{project_id}/documents",
        json={
            "project_id": project_id,
            "title": f"Specification in {status}",
            "doc_type": "SPEC",
            "status": status,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["loc"] == ["body", "status"]
    listed = api_client.get(f"/api/projects/{project_id}/documents", headers=auth_headers)
    assert listed.status_code == 200
    assert all(item["title"] != f"Specification in {status}" for item in listed.json()["items"])
