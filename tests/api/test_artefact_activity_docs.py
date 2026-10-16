"""Activity logging and docs facade REQ metadata for document-like artefacts."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

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


@pytest.fixture
def project(api_client: TestClient, auth_headers: dict[str, str]) -> dict:
    return create_project(api_client, auth_headers, "Activity Docs Project")


@pytest.fixture
def project_prefix(project: dict) -> str:
    return project["prefix"]


@pytest.fixture
def project_id(project: dict) -> int:
    return project["id"]


def test_requirement_docs_list_includes_type_and_origin(
    api_client: TestClient,
    auth_headers: dict[str, str],
    project_id: int,
    project_prefix: str,
):
    created = api_client.post(
        "/api/requirements",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "title": "Typed requirement",
            "req_type": "Safety",
            "req_origin": "Regulatory",
        },
    )
    assert created.status_code == 201, created.text

    listed = api_client.get(
        f"/api/projects/{project_prefix}/docs",
        headers=auth_headers,
        params={"type": "REQ"},
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["items"]
    match = next(
        (row for row in rows if row["doc_type"] == "REQ" and row["title"] == "Typed requirement"),
        None,
    )
    assert match is not None
    assert match["req_type"] == "Safety"
    assert match["req_origin"] == "Regulatory"


def test_requirement_activity_logged_on_create_and_update(
    api_client: TestClient,
    auth_headers: dict[str, str],
    project_id: int,
):
    created = api_client.post(
        "/api/requirements",
        headers=auth_headers,
        json={"project_id": project_id, "title": "Activity requirement"},
    )
    assert created.status_code == 201, created.text
    requirement_id = created.json()["id"]

    activity = api_client.get(
        f"/api/artefacts/requirement/{requirement_id}/activity",
        headers=auth_headers,
    )
    assert activity.status_code == 200, activity.text
    events = activity.json()
    assert any(event["event_type"] == "created" for event in events)

    updated = api_client.patch(
        f"/api/requirements/{requirement_id}",
        headers=auth_headers,
        json={"title": "Activity requirement updated"},
    )
    assert updated.status_code == 200, updated.text

    activity_after = api_client.get(
        f"/api/artefacts/requirement/{requirement_id}/activity",
        headers=auth_headers,
    )
    assert activity_after.status_code == 200, activity_after.text
    assert any(event["event_type"] == "updated" for event in activity_after.json())


def test_document_activity_logged_on_create(
    api_client: TestClient,
    auth_headers: dict[str, str],
    project_id: int,
):
    created = api_client.post(
        f"/api/projects/{project_id}/documents",
        headers=auth_headers,
        json={"project_id": project_id, "title": "Activity specification", "doc_type": "SPEC"},
    )
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]

    activity = api_client.get(
        f"/api/artefacts/document/{document_id}/activity",
        headers=auth_headers,
    )
    assert activity.status_code == 200, activity.text
    assert any(event["event_type"] == "created" for event in activity.json())


def _current_user_id(api_client: TestClient, auth_headers: dict[str, str]) -> int:
    me = api_client.get("/api/auth/me", headers=auth_headers)
    assert me.status_code == 200, me.text
    return me.json()["id"]


def _activity_event_types(
    api_client: TestClient,
    auth_headers: dict[str, str],
    artefact_type: str,
    artefact_id: int,
) -> list[str]:
    activity = api_client.get(
        f"/api/artefacts/{artefact_type}/{artefact_id}/activity",
        headers=auth_headers,
    )
    assert activity.status_code == 200, activity.text
    return [event["event_type"] for event in activity.json()]


def _review_document(api_client, auth_headers, artefact_type, artefact_id):
    """Record the assigned reviewer's proof for the creator's requested revision."""
    actor_id = _current_user_id(api_client, auth_headers)
    base = f"/api/artefacts/{artefact_type}/{artefact_id}"
    assigned = api_client.put(
        base + "/workflow/assignees",
        headers=auth_headers,
        json={"reviewer_id": actor_id, "approver_id": actor_id},
    )
    assert assigned.status_code == 200, assigned.text
    requested = api_client.post(base + "/requests", headers=auth_headers, json={"kind": "review"})
    assert requested.status_code == 201, requested.text
    comment = api_client.post(
        base + "/comments", headers=auth_headers, json={"body": "Reviewed this revision"}
    )
    assert comment.status_code == 201, comment.text
    return api_client.post(base + "/sign-off", headers=auth_headers, json={"step": "review"})


def test_requirement_workflow_activity_events(
    api_client: TestClient,
    auth_headers: dict[str, str],
    project_id: int,
):
    admin_id = _current_user_id(api_client, auth_headers)
    created = api_client.post(
        "/api/requirements",
        headers=auth_headers,
        json={"project_id": project_id, "title": "Workflow requirement"},
    )
    assert created.status_code == 201, created.text
    requirement_id = created.json()["id"]

    refused = api_client.patch(
        f"/api/requirements/{requirement_id}",
        headers=auth_headers,
        json={"reviewed_by_id": admin_id, "reviewed_at": "2026-05-12T10:00:00Z"},
    )
    assert refused.status_code == 422, refused.text
    reviewed = _review_document(api_client, auth_headers, "requirement", requirement_id)
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["reviewed_by_id"] == admin_id
    assert reviewed.json()["reviewed_at"].endswith("Z")
    reviewed_events = _activity_event_types(api_client, auth_headers, "requirement", requirement_id)
    assert "reviewed" in reviewed_events
    assert reviewed_events.count("updated") == 0

    approved = api_client.post(
        f"/api/artefacts/requirement/{requirement_id}/sign-off",
        headers=auth_headers,
        json={"step": "approve"},
    )
    assert approved.status_code == 200, approved.text
    approved_events = _activity_event_types(api_client, auth_headers, "requirement", requirement_id)
    assert "approved" in approved_events

    status_only = api_client.patch(
        f"/api/requirements/{requirement_id}",
        headers=auth_headers,
        json={"status": "Approved"},
    )
    assert status_only.status_code == 200, status_only.text
    status_events = _activity_event_types(api_client, auth_headers, "requirement", requirement_id)
    assert "approved" in status_events

    mixed = api_client.patch(
        f"/api/requirements/{requirement_id}",
        headers=auth_headers,
        json={"title": "Workflow requirement renamed", "status": "Draft"},
    )
    assert mixed.status_code == 409, mixed.text
    change = api_client.post(
        "/api/changes",
        headers=auth_headers,
        json={"project_id": project_id, "title": "Authorize a revised requirement"},
    )
    assert change.status_code == 201, change.text
    change_id = change.json()["id"]
    reviewed_change = _review_document(api_client, auth_headers, "change", change_id)
    assert reviewed_change.status_code == 200, reviewed_change.text
    approved_change = api_client.post(
        f"/api/artefacts/change/{change_id}/sign-off",
        headers=auth_headers,
        json={"step": "approve"},
    )
    assert approved_change.status_code == 200, approved_change.text
    linked = api_client.post(
        "/api/links",
        headers=auth_headers,
        json={
            "project_id": project_id,
            "source_type": "CHG",
            "source_id": change_id,
            "target_type": "REQ",
            "target_id": requirement_id,
            "role": "impacts",
        },
    )
    assert linked.status_code == 201, linked.text
    edited = api_client.patch(
        f"/api/requirements/{requirement_id}",
        headers=auth_headers,
        json={"title": "Workflow requirement renamed"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["status"] == "Draft"
    mixed_events = _activity_event_types(api_client, auth_headers, "requirement", requirement_id)
    assert "updated" in mixed_events
    assert "revision_started" in mixed_events


def test_test_case_workflow_activity_events(
    api_client: TestClient,
    auth_headers: dict[str, str],
    project_id: int,
):
    admin_id = _current_user_id(api_client, auth_headers)
    created = api_client.post(
        "/api/test-cases",
        headers=auth_headers,
        json={"project_id": project_id, "title": "Workflow test case"},
    )
    assert created.status_code == 201, created.text
    test_case_id = created.json()["id"]

    refused = api_client.patch(
        f"/api/test-cases/{test_case_id}",
        headers=auth_headers,
        json={"reviewed_by_id": admin_id, "reviewed_at": "2026-05-12T10:00:00Z"},
    )
    assert refused.status_code == 422, refused.text
    reviewed = _review_document(api_client, auth_headers, "test-case", test_case_id)
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["reviewed_by_id"] == admin_id
    assert reviewed.json()["reviewed_at"].endswith("Z")
    reviewed_events = _activity_event_types(api_client, auth_headers, "test-case", test_case_id)
    assert "reviewed" in reviewed_events
    assert reviewed_events.count("updated") == 0

    approved = api_client.post(
        f"/api/artefacts/test-case/{test_case_id}/sign-off",
        headers=auth_headers,
        json={"step": "approve"},
    )
    assert approved.status_code == 200, approved.text
    approved_events = _activity_event_types(api_client, auth_headers, "test-case", test_case_id)
    assert "approved" in approved_events

    status_only = api_client.patch(
        f"/api/test-cases/{test_case_id}",
        headers=auth_headers,
        json={"status": "Approved"},
    )
    assert status_only.status_code == 200, status_only.text
    status_events = _activity_event_types(api_client, auth_headers, "test-case", test_case_id)
    assert "approved" in status_events


def test_document_workflow_activity_events(
    api_client: TestClient,
    auth_headers: dict[str, str],
    project_id: int,
):
    created = api_client.post(
        f"/api/projects/{project_id}/documents",
        headers=auth_headers,
        json={"project_id": project_id, "title": "Workflow specification", "doc_type": "SPEC"},
    )
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]

    reviewed = _review_document(api_client, auth_headers, "document", document_id)
    assert reviewed.status_code == 200, reviewed.text
    reviewed_events = _activity_event_types(api_client, auth_headers, "document", document_id)
    assert "reviewed" in reviewed_events
    assert reviewed_events.count("updated") == 0

    approved = api_client.post(
        f"/api/artefacts/document/{document_id}/sign-off",
        headers=auth_headers,
        json={"step": "approve"},
    )
    assert approved.status_code == 200, approved.text
    approved_events = _activity_event_types(api_client, auth_headers, "document", document_id)
    assert "approved" in approved_events


def test_design_transition_logs_review_and_approval_activity(
    api_client: TestClient,
    auth_headers: dict[str, str],
    project_id: int,
):
    created = api_client.post(
        "/api/designs",
        headers=auth_headers,
        json={"project_id": project_id, "title": "Workflow design"},
    )
    assert created.status_code == 201, created.text
    design_id = created.json()["id"]

    review = _review_document(api_client, auth_headers, "design", design_id)
    assert review.status_code == 200, review.text
    review_events = _activity_event_types(api_client, auth_headers, "design", design_id)
    assert "reviewed" in review_events

    approved = api_client.post(
        f"/api/artefacts/design/{design_id}/sign-off",
        headers=auth_headers,
        json={"step": "approve"},
    )
    assert approved.status_code == 200, approved.text
    approved_events = _activity_event_types(api_client, auth_headers, "design", design_id)
    assert "approved" in approved_events
