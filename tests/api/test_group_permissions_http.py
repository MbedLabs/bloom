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
    assert denied.json()["detail"] == "Missing permission: create on REQ."

    mine = api_client.get(f"/api/projects/{project}/permissions", headers=headers).json()
    assert mine["REQ"] == ["view"]
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
    assert denied.json()["detail"] == "Missing permission: create on REQ."


def test_project_members_and_access_are_admin_only(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Direct")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    other = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    added = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "role": "maintainer"},
    )
    assert added.status_code == 201, added.text
    membership = added.json()["id"]
    _grant(api_client, admin, "Project Administrator", user["id"], project)

    assert _create(api_client, headers, "requirements", project).status_code == 201
    mine = api_client.get(f"/api/projects/{project}/permissions", headers=headers).json()
    assert "member" not in mine
    base = f"/api/projects/{project}"
    for method, path, body in (
        ("GET", f"{base}/members", None),
        ("POST", f"{base}/members", {"user_id": other["id"], "role": "maintainer"}),
        ("GET", f"{base}/members/{membership}", None),
        ("PATCH", f"{base}/members/{membership}", {"role": "external"}),
        ("DELETE", f"{base}/members/{membership}", None),
        ("GET", f"{base}/access", None),
    ):
        denied = api_client.request(method, path, headers=headers, json=body)
        assert denied.status_code == 403, (method, path, denied.text)
        assert denied.json()["detail"] == "Role 'maintainer' not authorized. Required: ['admin']"
    assert api_client.get(f"{base}/members", headers=admin).status_code == 200
    assert api_client.get(f"{base}/access", headers=admin).status_code == 200


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

    body["permissions"] = {"REQ": ["view"]}
    policy = api_client.post("/api/policies", headers=admin, json=body).json()
    patched = api_client.patch(
        f"/api/policies/{policy['id']}",
        headers=admin,
        json={"permissions": {"REQ": ["fly"]}},
    )
    assert patched.status_code == 400
    assert "unknown action 'fly' on 'REQ'" in patched.json()["detail"]


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


def test_document_permissions_follow_the_document_type(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Typed")["id"]
    policy = api_client.post(
        "/api/policies",
        headers=admin,
        json={
            "name": unique_name("Specifications"),
            "base_role": "maintainer",
            "permissions": {"SPEC": ["view", "edit"], "PRT": ["view"]},
        },
    )
    assert policy.status_code == 201, policy.text
    group = _create_group(api_client, admin, policy_id=policy.json()["id"])
    granted = api_client.post(
        f"/api/groups/{group['id']}/grants", headers=admin, json={"project_id": project}
    )
    assert granted.status_code == 201, granted.text
    user = _create_user(api_client, admin, role="maintainer")
    added = api_client.post(
        f"/api/groups/{group['id']}/members", headers=admin, json={"user_id": user["id"]}
    )
    assert added.status_code == 201, added.text
    headers = _headers_for(api_client, user["email"])

    def document(doc_type):
        created = api_client.post(
            f"/api/projects/{project}/documents",
            headers=admin,
            json={"project_id": project, "title": unique_name(doc_type), "doc_type": doc_type},
        )
        assert created.status_code == 201, created.text
        return created.json()["id"]

    specification, protocol = document("SPEC"), document("PRT")
    edited = api_client.patch(
        f"/api/documents/{specification}", headers=headers, json={"title": "Edited"}
    )
    assert edited.status_code == 200, edited.text
    denied = api_client.patch(
        f"/api/documents/{protocol}", headers=headers, json={"title": "Edited"}
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Missing permission: edit on PRT."
    retyped = api_client.patch(
        f"/api/documents/{specification}", headers=headers, json={"doc_type": "PRT"}
    )
    assert retyped.status_code == 403
    assert retyped.json()["detail"] == "Missing permission: edit on PRT."


def test_an_external_user_cannot_change_what_they_cannot_see(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Hidden")["id"]
    requirement = _create(api_client, admin, "requirements", project).json()
    test_case = _create(api_client, admin, "test-cases", project).json()
    assert requirement["visibility"] == "internal"
    user = _create_user(api_client, admin, role="external")
    headers = _headers_for(api_client, user["email"])
    _grant(api_client, admin, "Requirements Author", user["id"], project)
    _grant(api_client, admin, "Test Author", user["id"], project)

    for kind, row in (("requirements", requirement), ("test-cases", test_case)):
        edited = api_client.patch(f"/api/{kind}/{row['id']}", headers=headers, json={"title": "x"})
        assert edited.status_code == 404, edited.text
        deleted = api_client.delete(f"/api/{kind}/{row['id']}", headers=headers)
        assert deleted.status_code == 404, deleted.text
    assert (
        api_client.get(f"/api/requirements/{requirement['id']}", headers=admin).json()["title"]
        == requirement["title"]
    )


def test_a_user_outside_the_project_gets_404_by_id(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Elsewhere")["id"]
    requirement = _create(api_client, admin, "requirements", project).json()
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])

    edited = api_client.patch(
        f"/api/requirements/{requirement['id']}", headers=headers, json={"title": "x"}
    )
    assert edited.status_code == 404
    assert edited.json()["detail"] == "Requirement not found"


def test_every_change_by_id_hides_what_an_external_user_cannot_see(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Guarded")["id"]

    def made(path, body):
        response = api_client.post(path, headers=admin, json=body)
        assert response.status_code == 201, response.text
        return response.json()["id"]

    defect = made("/api/defects", {"project_id": project, "title": unique_name("defect")})
    campaign = made("/api/campaigns", {"project_id": project, "name": unique_name("campaign")})
    open_campaign = made(
        "/api/campaigns",
        {"project_id": project, "name": unique_name("campaign"), "visibility": "customer"},
    )
    suite = made("/api/test-suites", {"project_id": project, "name": unique_name("suite")})
    test_case = made("/api/test-cases", {"project_id": project, "title": unique_name("case")})
    document = made(
        f"/api/projects/{project}/documents", {"project_id": project, "title": unique_name("doc")}
    )
    section = made(f"/api/documents/{document}/sections", {"title": "Scope"})
    user = _create_user(api_client, admin, role="external")
    headers = _headers_for(api_client, user["email"])
    for policy in ("Requirements Author", "Test Author", "Design Author"):
        _grant(api_client, admin, policy, user["id"], project)

    attempts = [
        ("patch", f"/api/defects/{defect}", {"title": "x"}),
        ("post", f"/api/defects/{defect}/refresh-external", None),
        ("delete", f"/api/defects/{defect}", None),
        ("patch", f"/api/campaigns/{campaign}", {"name": "x"}),
        ("post", f"/api/campaigns/{campaign}/items?test_case_id={test_case}", None),
        ("delete", f"/api/campaigns/{campaign}", None),
        ("post", f"/api/test-suites/{suite}/items?test_case_id={test_case}", None),
        ("patch", f"/api/documents/{document}", {"title": "x"}),
        ("post", f"/api/documents/{document}/sections", {"title": "x"}),
        ("patch", f"/api/document-sections/{section}", {"title": "x"}),
        ("post", f"/api/documents/{document}/sections/reorder", {"section_orders": []}),
        ("delete", f"/api/document-sections/{section}", None),
        ("post", f"/api/campaigns/{open_campaign}/items?test_case_id={test_case}", None),
    ]
    for method, path, body in attempts:
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        response = getattr(api_client, method)(path, **kwargs)
        assert response.status_code == 404, (method, path, response.status_code, response.text)
        assert response.json()["detail"] != "Not Found", (method, path)


def test_an_external_user_still_changes_a_customer_row_they_can_see(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Shared")["id"]
    shared = api_client.post(
        "/api/test-cases",
        headers=admin,
        json={"project_id": project, "title": unique_name("case"), "visibility": "customer"},
    )
    assert shared.status_code == 201, shared.text
    user = _create_user(api_client, admin, role="external")
    headers = _headers_for(api_client, user["email"])
    _grant(api_client, admin, "Test Author", user["id"], project)

    edited = api_client.patch(
        f"/api/test-cases/{shared.json()['id']}", headers=headers, json={"title": "Renamed"}
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["title"] == "Renamed"


def test_an_external_user_cannot_change_an_item_of_a_hidden_campaign(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Items")["id"]
    case = _create(api_client, admin, "test-cases", project).json()["id"]
    created = api_client.post(
        "/api/campaigns",
        headers=admin,
        json={"project_id": project, "name": unique_name("c"), "test_case_ids": [case]},
    )
    assert created.status_code == 201, created.text
    campaign = created.json()["id"]
    item_id = created.json()["items"][0]["id"]
    user = _create_user(api_client, admin, role="external")
    headers = _headers_for(api_client, user["email"])
    _grant(api_client, admin, "Test Author", user["id"], project)

    changed = api_client.patch(
        f"/api/campaigns/{campaign}/items/{item_id}",
        headers=headers,
        json={"comment": "x"},
    )
    assert changed.status_code == 404, changed.text
    assert changed.json()["detail"] == "Campaign not found"
