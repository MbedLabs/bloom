"""require_permission over HTTP: group policies add to the role baseline, never remove.

A user with only a group grant is held to the group's policy matrix; a direct member
keeps exactly what the role allowed; the permissions endpoint reports the same set.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest
from fastapi.testclient import TestClient

from tests.api.test_groups_http import (
    _admin_headers,
    _create_group,
    _create_user,
    _headers_for,
)
from tests.conftest import create_project, unique_name
from tests.logic.test_reqif_import import SAMPLE_REQIF


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


def _external_on(api_client, admin, project, *policies):
    user = _create_user(api_client, admin, role="external")
    for policy in policies:
        _grant(api_client, admin, policy, user["id"], project)
    return _headers_for(api_client, user["email"])


def test_a_request_body_cannot_reach_a_hidden_artefact(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Bodies")["id"]
    hidden_requirement = _create(api_client, admin, "requirements", project).json()["id"]
    hidden_case = _create(api_client, admin, "test-cases", project).json()["id"]
    shown_case = api_client.post(
        "/api/test-cases",
        headers=admin,
        json={"project_id": project, "title": unique_name("case"), "visibility": "customer"},
    ).json()["id"]
    hidden_suite = api_client.post(
        "/api/test-suites", headers=admin, json={"project_id": project, "name": unique_name("s")}
    ).json()["id"]
    headers = _external_on(api_client, admin, project, "Requirements Author", "Test Author")

    child = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project, "title": unique_name("req"), "parent_id": hidden_requirement},
    )
    assert child.status_code == 404
    assert child.json()["detail"] == "Parent requirement not found"

    suite = api_client.post(
        "/api/test-suites",
        headers=headers,
        json={
            "project_id": project,
            "name": unique_name("s"),
            "test_case_ids": [hidden_case, shown_case],
        },
    )
    assert suite.status_code == 201, suite.text
    assert [item["test_case_id"] for item in suite.json()["items"]] == [shown_case]

    campaign = api_client.post(
        "/api/campaigns",
        headers=headers,
        json={"project_id": project, "name": unique_name("c"), "suite_ids": [hidden_suite]},
    )
    assert campaign.status_code == 404
    assert campaign.json()["detail"] == f"Suite {hidden_suite} not found"


def test_a_campaign_update_keeps_the_suites_the_editor_cannot_see(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Kept")["id"]

    def suite(visibility):
        return api_client.post(
            "/api/test-suites",
            headers=admin,
            json={"project_id": project, "name": unique_name("s"), "visibility": visibility},
        ).json()["id"]

    hidden, first, second = suite("internal"), suite("customer"), suite("customer")
    campaign = api_client.post(
        "/api/campaigns",
        headers=admin,
        json={
            "project_id": project,
            "name": unique_name("c"),
            "visibility": "customer",
            "suite_ids": [hidden, first],
        },
    ).json()["id"]
    headers = _external_on(api_client, admin, project, "Test Author")

    updated = api_client.patch(
        f"/api/campaigns/{campaign}", headers=headers, json={"suite_ids": [second]}
    )
    assert updated.status_code == 200, updated.text
    linked = api_client.get(f"/api/campaigns/{campaign}", headers=admin).json()["suites"]
    assert sorted(s["id"] for s in linked) == sorted([hidden, second])


def test_an_empty_suite_list_keeps_suites_outside_the_allowed_types(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Typed suites")["id"]
    suite = api_client.post(
        "/api/test-suites",
        headers=admin,
        json={"project_id": project, "name": unique_name("s"), "visibility": "customer"},
    ).json()["id"]
    campaign = api_client.post(
        "/api/campaigns",
        headers=admin,
        json={
            "project_id": project,
            "name": unique_name("c"),
            "visibility": "customer",
            "suite_ids": [suite],
        },
    ).json()["id"]
    policy = api_client.post(
        "/api/policies",
        headers=admin,
        json={
            "name": unique_name("Campaigns only"),
            "base_role": "external",
            "permissions": {"CMP": ["view", "comment", "edit", "plan"]},
            "doc_tag_scope": ["CMP"],
        },
    )
    assert policy.status_code == 201, policy.text
    group = _create_group(api_client, admin, policy_id=policy.json()["id"])
    granted = api_client.post(
        f"/api/groups/{group['id']}/grants", headers=admin, json={"project_id": project}
    )
    assert granted.status_code == 201, granted.text
    user = _create_user(api_client, admin, role="external")
    added = api_client.post(
        f"/api/groups/{group['id']}/members", headers=admin, json={"user_id": user["id"]}
    )
    assert added.status_code == 201, added.text
    headers = _headers_for(api_client, user["email"])

    updated = api_client.patch(
        f"/api/campaigns/{campaign}", headers=headers, json={"suite_ids": []}
    )
    assert updated.status_code == 200, updated.text
    linked = api_client.get(f"/api/campaigns/{campaign}", headers=admin).json()["suites"]
    assert [s["id"] for s in linked] == [suite]


@pytest.fixture
def many_imports(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "REQIF_IMPORTS_PER_15_MINUTES", 100)


def _policy_user(api_client, admin, permissions, *projects, role="maintainer", scope=None):
    policy = api_client.post(
        "/api/policies",
        headers=admin,
        json={
            "name": unique_name("Policy"),
            "base_role": role,
            "permissions": permissions,
            "doc_tag_scope": scope,
        },
    )
    assert policy.status_code == 201, policy.text
    group = _create_group(api_client, admin, policy_id=policy.json()["id"])
    for project in projects:
        granted = api_client.post(
            f"/api/groups/{group['id']}/grants", headers=admin, json={"project_id": project}
        )
        assert granted.status_code == 201, granted.text
    user = _create_user(api_client, admin, role=role)
    added = api_client.post(
        f"/api/groups/{group['id']}/members", headers=admin, json={"user_id": user["id"]}
    )
    assert added.status_code == 201, added.text
    return _headers_for(api_client, user["email"])


def _upload(api_client, headers, project, kind, name, content, **params):
    return api_client.post(
        f"/api/projects/{project}/import/{kind}",
        headers=headers,
        params=params,
        files={"file": (name, content, "application/octet-stream")},
    )


@pytest.mark.usefixtures("many_imports")
def test_a_copy_leaves_out_source_rows_the_user_cannot_see(api_client: TestClient):
    admin = _admin_headers(api_client)
    source = create_project(api_client, admin, "Copy source")["id"]
    target = create_project(api_client, admin, "Copy target")["id"]
    hidden = _create(api_client, admin, "requirements", source).json()["id"]
    shown = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": source, "title": unique_name("req"), "req_origin": "customer"},
    ).json()["id"]
    user = _create_user(api_client, admin, role="external")
    for project in (source, target):
        _grant(api_client, admin, "Requirements Author", user["id"], project)
    headers = _headers_for(api_client, user["email"])

    copied = api_client.post(
        f"/api/projects/{target}/import",
        headers=headers,
        json={"source_project_id": source, "doc_type": "REQ", "doc_ids": [hidden, shown]},
    )
    assert copied.status_code == 201, copied.text
    assert (copied.json()["imported"], copied.json()["skipped"]) == (1, 1)
    assert copied.json()["errors"] == [f"Requirement {hidden} not found in source project"]


@pytest.mark.usefixtures("many_imports")
def test_a_test_case_file_import_checks_edit_and_create_per_row(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Rows")["id"]
    existing = _create(api_client, admin, "test-cases", project).json()
    content = f"tc_id,title\n{existing['tc_id']},Changed\n,Brand new\n".encode()

    creator = _policy_user(api_client, admin, {"TC": ["view", "import", "create"]}, project)
    created = _upload(api_client, creator, project, "test-cases", "c.csv", content, format="csv")
    assert created.status_code == 201, created.text
    body = created.json()
    assert (body["created"], body["updated"], body["skipped"]) == (1, 0, 1)
    assert body["errors"] == ["row 1: not permitted"]
    kept = api_client.get(f"/api/test-cases/{existing['id']}", headers=admin).json()
    assert kept["title"] == existing["title"]

    editor = _policy_user(api_client, admin, {"TC": ["view", "import", "edit"]}, project)
    edited = _upload(api_client, editor, project, "test-cases", "c.csv", content, format="csv")
    assert edited.status_code == 201, edited.text
    body = edited.json()
    assert (body["created"], body["updated"], body["skipped"]) == (0, 1, 1)
    assert body["errors"] == ["row 2: not permitted"]
    changed = api_client.get(f"/api/test-cases/{existing['id']}", headers=admin).json()
    assert changed["title"] == "Changed"


@pytest.mark.usefixtures("many_imports")
def test_a_test_case_file_import_treats_a_hidden_test_case_as_new(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Hidden rows")["id"]
    hidden = _create(api_client, admin, "test-cases", project).json()
    headers = _external_on(api_client, admin, project, "Test Author")
    content = f"tc_id,title\n{hidden['tc_id']},Taken over\n".encode()

    imported = _upload(api_client, headers, project, "test-cases", "c.csv", content, format="csv")
    assert imported.status_code == 201, imported.text
    body = imported.json()
    assert (body["created"], body["updated"]) == (1, 0)
    assert body["new_ids"] != [hidden["tc_id"]]
    kept = api_client.get(f"/api/test-cases/{hidden['id']}", headers=admin).json()
    assert kept["title"] == hidden["title"]


@pytest.mark.usefixtures("many_imports")
def test_a_testrail_import_neither_reuses_nor_links_hidden_rows(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Rail")["id"]
    hidden = _create(api_client, admin, "requirements", project).json()["req_id"]
    shown = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": unique_name("req"), "req_origin": "customer"},
    ).json()["req_id"]
    export = (
        "<suite><sections><section><name>Boot</name><cases><case><id>C1</id>"
        f"<title>Cold boot</title><references>{hidden}, {shown}</references>"
        "</case></cases></section></sections></suite>"
    ).encode()

    def run(headers):
        response = _upload(api_client, headers, project, "testrail", "t.xml", export, format="xml")
        assert response.status_code == 201, response.text
        body = response.json()
        return body["created"], body["updated"], body["links_created"], len(body["suites_created"])

    assert run(admin) == (1, 0, 2, 1)
    assert run(_external_on(api_client, admin, project, "Test Author")) == (1, 0, 1, 1)
    assert run(admin) == (0, 1, 0, 0)


@pytest.mark.usefixtures("many_imports")
def test_a_reqif_import_does_not_reuse_hidden_requirements(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "ReqIF rows")["id"]

    def run(headers):
        response = _upload(api_client, headers, project, "reqif", "s.reqif", SAMPLE_REQIF)
        assert response.status_code == 201, response.text
        body = response.json()
        return body["imported"], body["skipped"], body["links_created"]

    assert run(admin) == (2, 0, 1)
    assert run(_external_on(api_client, admin, project, "Requirements Author")) == (2, 0, 1)
    assert run(admin) == (0, 2, 0)


@pytest.mark.usefixtures("many_imports")
def test_a_markdown_import_does_not_count_hidden_rows_as_duplicates(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Markdown rows")["id"]
    document = f"## [TC] {unique_name('case')}\nPower the board\n".encode()

    def run(headers):
        response = _upload(api_client, headers, project, "markdown", "d.md", document)
        assert response.status_code == 201, response.text
        return response.json()["artefacts_created"], response.json()["artefacts_skipped"]

    assert run(admin) == (1, 0)
    assert run(_external_on(api_client, admin, project, "Test Author")) == (1, 0)
    assert run(admin) == (0, 1)


@pytest.mark.usefixtures("many_imports")
def test_each_imported_row_needs_the_right_its_own_route_needs(api_client: TestClient):
    admin = _admin_headers(api_client)
    source = create_project(api_client, admin, "Rights source")["id"]
    target = create_project(api_client, admin, "Rights target")["id"]
    requirement = _create(api_client, admin, "requirements", source).json()

    copier = _policy_user(api_client, admin, {"REQ": ["view", "import", "export"]}, source, target)
    copied = api_client.post(
        f"/api/projects/{target}/import",
        headers=copier,
        json={"source_project_id": source, "doc_type": "REQ", "doc_ids": [requirement["id"]]},
    )
    assert copied.status_code == 201, copied.text
    assert copied.json()["errors"] == [f"Requirement {requirement['id']}: not permitted"]

    reader = _policy_user(api_client, admin, {"REQ": ["view", "import"]}, target)
    refused = _upload(api_client, reader, target, "reqif", "s.reqif", SAMPLE_REQIF)
    assert refused.status_code == 201, refused.text
    assert (refused.json()["imported"], refused.json()["skipped"]) == (0, 2)
    assert refused.json()["errors"] == [
        "object OBJ-1: not permitted",
        "object OBJ-2: not permitted",
    ]

    author = _policy_user(api_client, admin, {"REQ": ["view", "import", "create"]}, target)
    unlinked = _upload(api_client, author, target, "reqif", "s.reqif", SAMPLE_REQIF)
    assert unlinked.status_code == 201, unlinked.text
    assert (unlinked.json()["imported"], unlinked.json()["links_created"]) == (2, 0)
    assert unlinked.json()["errors"] == ["relation REL-1: not permitted"]

    tester = _policy_user(
        api_client, admin, {"REQ": ["view"], "TC": ["view", "import", "create"]}, source
    )
    export = (
        "<suite><sections><section><name>Boot</name><cases><case><id>C1</id>"
        f"<title>Cold boot</title><references>{requirement['req_id']}</references>"
        "</case></cases></section></sections></suite>"
    ).encode()
    railed = _upload(api_client, tester, source, "testrail", "t.xml", export, format="xml")
    assert railed.status_code == 201, railed.text
    body = railed.json()
    assert (body["created"], body["links_created"], body["suites_created"]) == (1, 0, [])
    assert body["errors"] == [
        "case C1: links not permitted",
        "case C1: adding to suite Boot not permitted",
    ]
    cases = api_client.get(f"/api/test-cases?project_id={source}", headers=admin).json()["items"]
    imported = next(c for c in cases if c["tc_id"] == body["new_ids"][0])
    assert requirement["req_id"] in imported["description"]

    title = unique_name("case")
    document = f"## [TC] {title}\nPower the board\n".encode()
    marked = _upload(
        api_client,
        _policy_user(api_client, admin, {"TC": ["view", "import"]}, target),
        target,
        "markdown",
        "d.md",
        document,
    )
    assert marked.status_code == 201, marked.text
    assert (marked.json()["artefacts_created"], marked.json()["artefacts_skipped"]) == (0, 1)
    assert marked.json()["errors"] == [f"section {title}: not permitted"]


@pytest.mark.usefixtures("many_imports")
def test_a_testrail_case_or_suite_without_its_right_is_reported(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Rail rights")["id"]

    def export(*ids):
        cases = "".join(f"<case><id>{i}</id><title>Case {i}</title></case>" for i in ids)
        return (
            f"<suite><sections><section><name>Boot</name><cases>{cases}</cases>"
            "</section></sections></suite>"
        ).encode()

    planner = _policy_user(
        api_client, admin, {"TC": ["view", "import", "create"], "TS": ["view", "plan"]}, project
    )
    planned = _upload(api_client, planner, project, "testrail", "t.xml", export("C1"), format="xml")
    assert planned.status_code == 201, planned.text
    assert (planned.json()["created"], planned.json()["suites_created"]) == (1, [])
    assert planned.json()["errors"] == ["case C1: creating suite Boot not permitted"]

    reader = _policy_user(api_client, admin, {"TC": ["view", "import"]}, project)
    refused = _upload(
        api_client, reader, project, "testrail", "t.xml", export("C1", "C2"), format="xml"
    )
    assert refused.status_code == 201, refused.text
    body = refused.json()
    assert (body["created"], body["updated"], body["skipped"]) == (0, 0, 2)
    assert body["errors"] == ["case C1: not permitted", "case C2: not permitted"]


@pytest.mark.usefixtures("many_imports")
def test_a_markdown_duplicate_of_a_hidden_type_is_not_a_duplicate(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Markdown types")["id"]
    document = f"## [TC] {unique_name('case')}\nPower the board\n".encode()
    outside = _policy_user(
        api_client,
        admin,
        {"TC": ["view", "import", "create"]},
        project,
        role="external",
        scope=["REQ"],
    )

    def run(headers):
        response = _upload(api_client, headers, project, "markdown", "d.md", document)
        assert response.status_code == 201, response.text
        return response.json()["artefacts_created"], response.json()["artefacts_skipped"]

    assert run(admin) == (1, 0)
    assert run(outside) == (1, 0)
