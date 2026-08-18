"""HTTP coverage for typed link rule enforcement."""

import asyncio
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import asyncpg
import pytest
from fastapi.testclient import TestClient

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


def _insert_legacy_link(
    *,
    project_id: int,
    source_type: str,
    source_id: int,
    target_type: str,
    target_id: int,
    role: str,
) -> None:
    async def insert() -> None:
        database_url = (os.environ.get("DATABASE_URL") or os.environ["BLOOM_DATABASE_URL"]).replace(
            "postgresql+asyncpg://", "postgresql://", 1
        )
        connection = await asyncpg.connect(database_url)
        try:
            await connection.execute(
                """
                INSERT INTO artefact_links (
                    project_id,
                    source_type,
                    source_id,
                    target_type,
                    target_id,
                    role,
                    suspect,
                    created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, FALSE, CURRENT_TIMESTAMP)
                """,
                project_id,
                source_type,
                source_id,
                target_type,
                target_id,
                role,
            )
        finally:
            await connection.close()

    asyncio.run(insert())


def test_create_link_rejects_forbidden_role_pair(
    api_client: TestClient,
    auth_headers: dict[str, str],
):
    project_id = create_project(api_client, auth_headers, "Link Rules Project")["id"]

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


def test_existing_legacy_relationship_is_visible_and_prevents_duplicate(
    api_client: TestClient,
    auth_headers: dict[str, str],
):
    project_id = create_project(api_client, auth_headers, "Legacy Link Project")["id"]

    concept = api_client.post(
        "/api/test-concepts",
        headers=auth_headers,
        json={"project_id": project_id, "name": "Existing concept"},
    )
    assert concept.status_code == 201
    concept_id = concept.json()["id"]

    test_case = api_client.post(
        "/api/test-cases",
        headers=auth_headers,
        json={"project_id": project_id, "title": "Existing test case"},
    )
    assert test_case.status_code == 201
    test_case_id = test_case.json()["id"]

    _insert_legacy_link(
        project_id=project_id,
        source_type="TCO",
        source_id=concept_id,
        target_type="TC",
        target_id=test_case_id,
        role="implements",
    )

    listed = api_client.get(
        "/api/links",
        headers=auth_headers,
        params={
            "project_id": project_id,
            "source_type": "CPT",
            "source_id": concept_id,
        },
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["source_type"] == "CPT"
    assert listed.json()[0]["target_type"] == "TC"

    duplicate = api_client.post(
        "/api/links",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "source_type": "CPT",
            "source_id": concept_id,
            "target_type": "TC",
            "target_id": test_case_id,
            "role": "implements",
        },
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Link already exists"
