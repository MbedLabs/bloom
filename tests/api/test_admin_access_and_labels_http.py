"""Numeric document addresses, access requests from people who hold the access, and the
labels access requests and the audit log show for their targets."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest
from fastapi.testclient import TestClient

from app.api import access_requests as access_requests_api
from tests.access_fixtures import add_policy_member
from tests.api.test_groups_http import _admin_headers, _create_user, _headers_for
from tests.conftest import create_project


@pytest.fixture
def sent_mail(monkeypatch):
    """Capture the access request emails."""
    sent = []
    monkeypatch.setattr(
        access_requests_api, "send_access_request_email", lambda **kwargs: sent.append(kwargs)
    )
    return sent


@pytest.fixture
def scene(api_client: TestClient):
    """A project with one requirement, a member who may not read requirements and a member
    who may."""
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Labels")
    requirement = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project["id"], "title": "Numeric address", "status": "Draft"},
    )
    assert requirement.status_code in (200, 201), requirement.text
    hidden = _create_user(api_client, admin, role="maintainer")
    reader = _create_user(api_client, admin, role="maintainer")
    for person, permissions in ((hidden, {"TC": ["view"]}), (reader, {"REQ": ["view"]})):
        member = add_policy_member(
            api_client,
            headers=admin,
            url=f"/api/projects/{project['id']}/members",
            user_id=person["id"],
            permissions=permissions,
        )
        assert member.status_code == 201, member.text
    return {
        "admin": admin,
        "project": project,
        "requirement": requirement.json(),
        "hidden": hidden,
        "hidden_headers": _headers_for(api_client, hidden["email"]),
        "reader": reader,
        "reader_headers": _headers_for(api_client, reader["email"]),
    }


def test_a_database_id_in_a_document_address_opens_the_item(api_client: TestClient, scene):
    prefix = scene["project"]["prefix"]
    requirement = scene["requirement"]
    path = f"/api/projects/{prefix}/docs/requirements"

    by_number = api_client.get(f"{path}/{requirement['id']}", headers=scene["admin"])
    by_doc_id = api_client.get(f"{path}/{requirement['req_id']}", headers=scene["admin"])
    missing = api_client.get(f"{path}/999999999", headers=scene["admin"])
    hidden = api_client.get(f"{path}/{requirement['id']}", headers=scene["hidden_headers"])
    reader = api_client.get(f"{path}/{requirement['id']}", headers=scene["reader_headers"])

    assert by_number.status_code == 200, by_number.text
    assert by_number.json()["doc_id"] == requirement["req_id"]
    assert by_number.json()["id"] == by_doc_id.json()["id"] == requirement["id"]
    assert missing.status_code == 404
    assert hidden.status_code == 404
    assert reader.status_code == 200
    assert reader.json()["doc_id"] == requirement["req_id"]


def test_an_administrator_cannot_request_access(api_client: TestClient, scene, sent_mail):
    response = api_client.post(
        "/api/access-requests",
        headers=scene["admin"],
        json={
            "resource_type": "requirement",
            "resource_ref": str(scene["requirement"]["id"]),
            "project_prefix": scene["project"]["prefix"],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Administrators hold every access, so there is nothing to request."
    )
    assert sent_mail == []


def test_a_user_who_can_open_the_resource_cannot_request_it(
    api_client: TestClient, scene, sent_mail
):
    prefix = scene["project"]["prefix"]
    requirement = scene["requirement"]

    project = api_client.post(
        "/api/access-requests",
        headers=scene["hidden_headers"],
        json={"resource_type": "project", "resource_ref": prefix, "project_prefix": prefix},
    )
    item = api_client.post(
        "/api/access-requests",
        headers=scene["reader_headers"],
        json={
            "resource_type": "requirement",
            "resource_ref": str(requirement["id"]),
            "project_prefix": prefix,
        },
    )

    assert project.status_code == 409
    assert project.json()["detail"] == f"You already have access to {prefix}."
    assert item.status_code == 409
    assert item.json()["detail"] == f"You already have access to {requirement['req_id']}."
    assert sent_mail == []


def test_requests_name_the_document_for_administrators_only(
    api_client: TestClient, scene, sent_mail
):
    prefix = scene["project"]["prefix"]
    requirement = scene["requirement"]
    body = {
        "resource_type": "document",
        "resource_ref": str(requirement["id"]),
        "project_prefix": prefix,
    }

    created = api_client.post("/api/access-requests", headers=scene["hidden_headers"], json=body)
    mine = api_client.get("/api/access-requests/mine", headers=scene["hidden_headers"], params=body)
    gone = api_client.post(
        "/api/access-requests",
        headers=scene["hidden_headers"],
        json={**body, "resource_ref": "999999999"},
    )
    listed = api_client.get(
        "/api/access-requests", headers=scene["admin"], params={"project_prefix": prefix}
    )

    assert created.status_code == 201, created.text
    assert created.json()["resource_label"] == str(requirement["id"])
    assert mine.json()["resource_label"] == str(requirement["id"])
    assert gone.status_code == 201, gone.text
    labels = {row["id"]: row["resource_label"] for row in listed.json()}
    assert labels[created.json()["id"]] == requirement["req_id"]
    assert labels[gone.json()["id"]] == "999999999 (deleted)"
    recipients = {mail["to_email"] for mail in sent_mail}
    assert scene["hidden"]["email"] not in recipients
    assert recipients
    assert sent_mail[0]["resource"] == requirement["req_id"]


def test_the_audit_log_names_targets_and_actors(api_client: TestClient, scene):
    requirement = scene["requirement"]
    member = scene["hidden"]
    assert api_client.get(f"/api/requirements/{requirement['id']}", headers=scene["admin"])
    assert api_client.get(f"/api/users/{member['id']}", headers=scene["admin"])
    api_client.get("/api/requirements/999999998", headers=scene["admin"])

    def event(target_type, target_id):
        page = api_client.get(
            "/api/audit",
            headers=scene["admin"],
            params={
                "action": "api.request",
                "target_type": target_type,
                "target_id": str(target_id),
            },
        )
        assert page.status_code == 200, page.text
        return page.json()["items"][0]

    found = event("requirement", requirement["id"])
    assert found["target_label"] == f"requirement {requirement['req_id']}"
    assert found["actor_label"] == found["actor_name"]
    assert event("user", member["id"])["target_label"] == "user Group Member"
    assert event("requirement", 999999998)["target_label"] == "requirement 999999998 (deleted)"
