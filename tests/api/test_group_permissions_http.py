"""require_permission over HTTP: group policies add to the role baseline, never remove.

A user with only a group grant is held to the group's policy matrix; a direct member
keeps exactly what the role allowed; the permissions endpoint reports the same set.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

from tests.api.test_groups_http import (
    _admin_headers,
    _create_group,
    _create_user,
    _headers_for,
)
from tests.conftest import create_project, unique_name


def _default_policy_id(api_client, headers, name) -> int:
    policies = api_client.get("/api/policies", headers=headers).json()
    return next(p["id"] for p in policies if p["name"] == name)


def _grant(api_client, headers, policy_name, user_id, project_id) -> None:
    group = _create_group(
        api_client, headers, policy_id=_default_policy_id(api_client, headers, policy_name)
    )
    granted = api_client.post(
        f"/api/groups/{group['id']}/grants", headers=headers, json={"project_id": project_id}
    )
    assert granted.status_code == 201, granted.text
    added = api_client.post(
        f"/api/groups/{group['id']}/members", headers=headers, json={"user_id": user_id}
    )
    assert added.status_code == 201, added.text


def _create(api_client, headers, kind, project_id):
    return api_client.post(
        f"/api/{kind}", headers=headers, json={"project_id": project_id, "title": unique_name(kind)}
    )


def test_read_only_group_reads_but_cannot_write(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Viewed")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    _grant(api_client, admin, "Read Only", user["id"], project)

    listed = api_client.get(f"/api/requirements?project_id={project}", headers=headers)
    assert listed.status_code == 200, listed.text
    denied = _create(api_client, headers, "requirements", project)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Missing permission: create on requirement."

    mine = api_client.get(f"/api/projects/{project}/permissions", headers=headers).json()
    assert mine["requirement"] == ["view"]
    assert "member" not in mine


def test_group_policy_adds_to_an_external_role(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Tested")["id"]
    user = _create_user(api_client, admin, role="external")
    headers = _headers_for(api_client, user["email"])
    _grant(api_client, admin, "Test Author", user["id"], project)

    assert _create(api_client, headers, "test-cases", project).status_code == 201
    denied = _create(api_client, headers, "requirements", project)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Missing permission: create on requirement."


def test_direct_maintainer_is_unchanged_and_members_need_a_policy(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Direct")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    added = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "role": "maintainer"},
    )
    assert added.status_code == 201, added.text

    assert _create(api_client, headers, "requirements", project).status_code == 201
    members = api_client.get(f"/api/projects/{project}/members", headers=headers)
    assert members.status_code == 403
    assert members.json()["detail"] == "Missing permission: view on member."

    _grant(api_client, admin, "Project Administrator", user["id"], project)
    assert api_client.get(f"/api/projects/{project}/members", headers=headers).status_code == 200


def test_no_access_and_admin(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Closed")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])

    denied = _create(api_client, headers, "requirements", project)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "User is not assigned to this project."
    assert api_client.get(f"/api/projects/{project}/permissions", headers=headers).json() == {}
    assert api_client.get(f"/api/projects/{project}/permissions", headers=admin).json() == {
        "*": ["*"]
    }
    assert api_client.get(f"/api/projects/{project}/members", headers=admin).status_code == 200


def test_policy_matrix_is_validated(api_client: TestClient):
    admin = _admin_headers(api_client)
    body = {
        "name": unique_name("Policy"),
        "description": "Bad matrix",
        "base_role": "maintainer",
        "permissions": {"widget": ["view"]},
    }
    created = api_client.post("/api/policies", headers=admin, json=body)
    assert created.status_code == 400
    assert created.json()["detail"] == "Invalid permissions: unknown resource 'widget'"

    body["permissions"] = {"requirement": ["view"]}
    policy = api_client.post("/api/policies", headers=admin, json=body).json()
    patched = api_client.patch(
        f"/api/policies/{policy['id']}",
        headers=admin,
        json={"permissions": {"requirement": ["fly"]}},
    )
    assert patched.status_code == 400
    assert "unknown action 'fly' on 'requirement'" in patched.json()["detail"]


def test_access_lists_everyone_with_access_and_why(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Origins")["id"]
    direct = _create_user(api_client, admin, role="maintainer")
    grouped = _create_user(api_client, admin, role="maintainer")
    everywhere = _create_user(api_client, admin, role="external")
    api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": direct["id"], "role": "maintainer"},
    )
    _grant(api_client, admin, "Test Author", grouped["id"], project)
    _grant(api_client, admin, "Test Author", direct["id"], project)
    all_group = _create_group(
        api_client, admin, policy_id=_default_policy_id(api_client, admin, "Read Only")
    )
    granted = api_client.post(
        f"/api/groups/{all_group['id']}/grants", headers=admin, json={"project_id": None}
    )
    assert granted.status_code == 201, granted.text
    api_client.post(
        f"/api/groups/{all_group['id']}/members", headers=admin, json={"user_id": everywhere["id"]}
    )

    access = api_client.get(f"/api/projects/{project}/access", headers=admin)
    assert access.status_code == 200, access.text
    by_user = {entry["user_id"]: entry["origins"] for entry in access.json()}
    assert by_user[direct["id"]][0] == {
        "kind": "direct",
        "role": "maintainer",
        "group": None,
        "policy": None,
        "all_projects": False,
    }
    assert [(o["kind"], o["policy"]) for o in by_user[direct["id"]][1:]] == [
        ("group", "Test Author")
    ]
    assert by_user[grouped["id"]][0]["policy"] == "Test Author"
    assert by_user[grouped["id"]][0]["all_projects"] is False
    assert by_user[everywhere["id"]][0]["all_projects"] is True
    assert by_user[everywhere["id"]][0]["group"] == all_group["name"]

    denied = api_client.get(
        f"/api/projects/{project}/access", headers=_headers_for(api_client, direct["email"])
    )
    assert denied.status_code == 403
