"""Explicit project policies and whole artefact scopes enforced over HTTP."""

import os
import re

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest
from fastapi.testclient import TestClient

from tests.access_fixtures import (
    add_policy_member,
    keep_matrix,
    scenario_permissions,
    scenario_rules,
)
from tests.api.test_groups_http import (
    _admin_headers,
    _create_group,
    _create_user,
    _headers_for,
)
from tests.conftest import create_project, unique_name
from tests.logic.test_reqif_import import SAMPLE_REQIF


def _default_policy_id(api_client, headers, name) -> int:
    """Create an explicit custom policy for this retained test scenario."""
    policy = api_client.post(
        "/api/policies",
        headers=headers,
        json={
            "name": unique_name(name),
            "rules": scenario_rules(
                scenario_permissions(name),
                "customer" if name == "External Reader" else "internal",
                ["REQ", "TC", "CPT", "CMP"] if name == "External Reader" else None,
            ),
        },
    )
    assert policy.status_code == 201, policy.text
    keep_matrix(policy.json()["id"], scenario_permissions(name))
    return policy.json()["id"]


def _grant(api_client, headers, policy_name, user_id, project_id) -> None:
    group = _create_group(
        api_client, headers, policy_id=_default_policy_id(api_client, headers, policy_name)
    )
    granted = api_client.post(
        f"/api/groups/{group['id']}/grants",
        headers=headers,
        json={"project_id": project_id},
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


def test_project_content_grant_cannot_manage_access(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Direct")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    other = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    added = add_policy_member(
        api_client,
        headers=admin,
        url=f"/api/projects/{project}/members",
        user_id=user["id"],
        permissions={"*": ["*"]},
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
        assert denied.json()["detail"] == "Application permission is required"
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


def test_policy_rules_are_validated_on_update(api_client: TestClient):
    admin = _admin_headers(api_client)
    body = {
        "name": unique_name("Policy"),
        "description": "Bad rules",
        "rules": {"widget": {"read": True}},
    }
    created = api_client.post("/api/policies", headers=admin, json=body)
    assert created.status_code == 400
    assert created.json()["detail"] == "Unknown resources: ['widget']"

    body["rules"] = {"REQ": {"read": True, "visibility": ["internal"]}}
    policy = api_client.post("/api/policies", headers=admin, json=body).json()
    patched = api_client.patch(
        f"/api/policies/{policy['id']}",
        headers=admin,
        json={"rules": {"REQ": {"write": True}}},
    )
    assert patched.status_code == 400
    assert patched.json()["detail"] == "Choose at least one tag for REQ."


def test_access_report_excludes_group_rules_replaced_by_an_explicit_entry(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Origins")["id"]
    other = create_project(api_client, admin, "Other origins")["id"]
    direct = _create_user(api_client, admin, role="maintainer")
    grouped = _create_user(api_client, admin, role="maintainer")
    added = add_policy_member(
        api_client,
        headers=admin,
        url=f"/api/projects/{project}/members",
        user_id=direct["id"],
        permissions={"*": ["*"]},
    )
    assert added.status_code == 201, added.text
    _grant(api_client, admin, "Test Author", direct["id"], project)
    _grant(api_client, admin, "Test Author", grouped["id"], project)
    access = api_client.get(f"/api/projects/{project}/access", headers=admin)
    assert access.status_code == 200, access.text
    by_user = {entry["user_id"]: entry["origins"] for entry in access.json()}
    assert [origin["kind"] for origin in by_user[direct["id"]]] == ["direct"]
    assert all(origin["policies"] and not origin["owner"] for origin in by_user[direct["id"]])
    assert by_user[grouped["id"]][0]["kind"] == "group"
    assert by_user[grouped["id"]][0]["policies"][0].startswith("Test Author ")
    elsewhere = api_client.get(f"/api/projects/{other}/access", headers=admin).json()
    assert all(entry["user_id"] not in {direct["id"], grouped["id"]} for entry in elsewhere)
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
            "rules": scenario_rules({"SPEC": ["view", "edit"], "PRT": ["view"]}),
        },
    )
    assert policy.status_code == 201, policy.text
    group = _create_group(api_client, admin, policy_id=policy.json()["id"])
    granted = api_client.post(
        f"/api/groups/{group['id']}/grants",
        headers=admin,
        json={"project_id": project},
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
    own_campaign = api_client.post(
        "/api/campaigns", headers=headers, json={"project_id": project, "name": unique_name("c")}
    )
    assert own_campaign.status_code == 201, own_campaign.text

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
        (
            "post",
            f"/api/campaigns/{own_campaign.json()['id']}/items?test_case_id={test_case}",
            None,
        ),
    ]
    for method, path, body in attempts:
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        response = getattr(api_client, method)(path, **kwargs)
        assert response.status_code == 404, (method, path, response.status_code, response.text)
        assert response.json()["detail"] != "Not Found", (method, path)


def test_an_external_user_changes_only_the_customer_rows_they_created(api_client: TestClient):
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
    own = api_client.post(
        "/api/test-cases", headers=headers, json={"project_id": project, "title": unique_name("c")}
    )
    assert own.status_code == 201, own.text

    edited = api_client.patch(
        f"/api/test-cases/{own.json()['id']}", headers=headers, json={"title": "Renamed"}
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["title"] == "Renamed"
    refused = api_client.patch(
        f"/api/test-cases/{shared.json()['id']}", headers=headers, json={"title": "Renamed"}
    )
    assert refused.status_code == 403
    assert refused.json()["detail"] == "External users change only what they created."


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
    headers = _external_on(api_client, admin, project, "Test Author")
    campaign = api_client.post(
        "/api/campaigns", headers=headers, json={"project_id": project, "name": unique_name("c")}
    ).json()["id"]
    linked = api_client.patch(
        f"/api/campaigns/{campaign}", headers=admin, json={"suite_ids": [hidden, first]}
    )
    assert linked.status_code == 200, linked.text

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
    policy = api_client.post(
        "/api/policies",
        headers=admin,
        json={
            "name": unique_name("Campaigns only"),
            "rules": scenario_rules(
                {"CMP": ["view", "create", "edit", "plan"]}, "customer", ["CMP"]
            ),
        },
    )
    assert policy.status_code == 201, policy.text
    group = _create_group(api_client, admin, policy_id=policy.json()["id"])
    granted = api_client.post(
        f"/api/groups/{group['id']}/grants",
        headers=admin,
        json={"project_id": project},
    )
    assert granted.status_code == 201, granted.text
    user = _create_user(api_client, admin, role="external")
    added = api_client.post(
        f"/api/groups/{group['id']}/members", headers=admin, json={"user_id": user["id"]}
    )
    assert added.status_code == 201, added.text
    headers = _headers_for(api_client, user["email"])
    campaign = api_client.post(
        "/api/campaigns", headers=headers, json={"project_id": project, "name": unique_name("c")}
    ).json()["id"]
    linked = api_client.patch(
        f"/api/campaigns/{campaign}", headers=admin, json={"suite_ids": [suite]}
    )
    assert linked.status_code == 200, linked.text

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


def _policy_user(
    api_client, admin, permissions, *projects, role="maintainer", scope=None, return_user=False
):
    """Grant the explicit group policy and return authentication with an optional actor."""
    policy = api_client.post(
        "/api/policies",
        headers=admin,
        json={
            "name": unique_name("Policy"),
            "rules": scenario_rules(
                permissions, "customer" if role == "external" else "internal", scope
            ),
        },
    )
    assert policy.status_code == 201, policy.text
    keep_matrix(policy.json()["id"], permissions)
    group = _create_group(api_client, admin, policy_id=policy.json()["id"])
    for project in projects:
        granted = api_client.post(
            f"/api/groups/{group['id']}/grants",
            headers=admin,
            json={"project_id": project},
        )
        assert granted.status_code == 201, granted.text
    user = _create_user(api_client, admin, role=role)
    added = api_client.post(
        f"/api/groups/{group['id']}/members", headers=admin, json={"user_id": user["id"]}
    )
    assert added.status_code == 201, added.text
    headers = _headers_for(api_client, user["email"])
    return (user, headers) if return_user else headers


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
    external = _external_on(api_client, admin, project, "Test Author", "Requirements Author")
    shown = _create(api_client, external, "requirements", project).json()["req_id"]
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
    assert run(external) == (1, 0, 1, 1)
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
def test_a_markdown_import_cannot_create_a_type_outside_its_policy_scope(api_client: TestClient):
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
    accepted = _upload(api_client, admin, project, "markdown", "d.md", document)
    assert accepted.status_code == 201, accepted.text
    refused = _upload(api_client, outside, project, "markdown", "d.md", document)
    assert refused.status_code == 403, refused.text
    cases = api_client.get(f"/api/test-cases?project_id={project}", headers=admin).json()["items"]
    assert len(cases) == 1


def test_adding_a_test_case_to_a_campaign_returns_the_item(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Items added")["id"]
    planner = _policy_user(api_client, admin, {"CMP": ["view", "plan"], "TC": ["view"]}, project)

    for headers in (admin, planner):
        case = _create(api_client, admin, "test-cases", project).json()
        campaign = api_client.post(
            "/api/campaigns", headers=admin, json={"project_id": project, "name": unique_name("c")}
        ).json()["id"]
        added = api_client.post(
            f"/api/campaigns/{campaign}/items?test_case_id={case['id']}", headers=headers
        )
        assert added.status_code == 201, added.text
        body = added.json()
        assert (body["campaign_id"], body["test_case_id"], body["status"]) == (
            campaign,
            case["id"],
            "Pending",
        )
        assert body["test_case"]["tc_id"] == case["tc_id"]
        saved = api_client.get(f"/api/campaigns/{campaign}", headers=admin).json()["items"]
        assert [(i["id"], i["test_case_id"]) for i in saved] == [(body["id"], case["id"])]


def _external_author(api_client, admin, project):
    """An external user holding the requirements, test and design author policies."""
    return _external_on(
        api_client, admin, project, "Requirements Author", "Test Author", "Design Author"
    )


def test_an_external_users_creations_are_customer_and_start_in_their_first_status(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Created outside")["id"]
    headers = _external_author(api_client, admin, project)

    def create(path, **body):
        response = api_client.post(path, headers=headers, json={"project_id": project, **body})
        assert response.status_code == 201, (path, response.text)
        return response.json()

    requirement = create("/api/requirements", title=unique_name("req"))
    assert (requirement["visibility"], requirement["req_origin"], requirement["status"]) == (
        "customer",
        "Customer",
        "Draft",
    )
    assert create("/api/test-cases", title=unique_name("tc"))["visibility"] == "customer"
    design = create("/api/designs", title=unique_name("des"))
    assert (design["visibility"], design["status"]) == ("customer", "Draft")
    defect = create("/api/defects", title=unique_name("def"))
    assert (defect["visibility"], defect["status"]) == ("customer", "Open")
    campaign = create("/api/campaigns", name=unique_name("cmp"))
    assert (campaign["visibility"], campaign["status"]) == ("customer", "Planned")
    assert create("/api/test-suites", name=unique_name("ts"))["visibility"] == "customer"

    refusals = [
        ("/api/test-cases", {"visibility": "internal"}, "create customer artefacts only"),
        ("/api/requirements", {"req_origin": "Internal"}, "create customer artefacts only"),
        ("/api/test-cases", {"status": "Approved"}, "create in status Draft"),
        ("/api/defects", {"status": "Triaged"}, "create in status Open"),
    ]
    for path, extra, message in refusals:
        refused = api_client.post(
            path,
            headers=headers,
            json={"project_id": project, "title": unique_name("x"), **extra},
        )
        assert refused.status_code == 403, (path, refused.text)
        assert message in refused.json()["detail"]


def test_an_external_user_keeps_visibility_and_sets_only_draft(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Draft only")["id"]
    headers = _external_author(api_client, admin, project)
    case = _create(api_client, headers, "test-cases", project).json()["id"]
    requirement = _create(api_client, headers, "requirements", project).json()["id"]
    defect = _create(api_client, headers, "defects", project).json()["id"]

    def patch(path, body):
        return api_client.patch(path, headers=headers, json=body)

    assert patch(f"/api/test-cases/{case}", {"visibility": "internal"}).status_code == 403
    assert patch(f"/api/test-cases/{case}", {"visibility": "customer"}).status_code == 200
    assert patch(f"/api/requirements/{requirement}", {"req_origin": "Internal"}).status_code == 403
    refused = patch(f"/api/test-cases/{case}", {"status": "Review"})
    assert refused.status_code == 403
    assert refused.json()["detail"] == "External users set the status only to Draft."
    moved = api_client.post(
        f"/api/artefacts/test-case/{case}/requests", headers=headers, json={"kind": "review"}
    )
    assert moved.status_code == 201, moved.text
    stored = api_client.get(f"/api/test-cases/{case}", headers=admin)
    assert stored.status_code == 200, stored.text
    assert stored.json()["status"] == "Review"
    assert patch(f"/api/test-cases/{case}", {"status": "Draft"}).status_code == 409
    fixed = patch(f"/api/defects/{defect}", {"status": "Triaged"})
    assert fixed.status_code == 403
    assert "defects, risks, changes or campaigns" in fixed.json()["detail"]


def test_an_external_user_changes_no_part_of_what_others_created(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Others")["id"]

    def made(path, body):
        response = api_client.post(path, headers=admin, json={"project_id": project, **body})
        assert response.status_code == 201, response.text
        return response.json()

    customer = {"visibility": "customer"}
    case = made("/api/test-cases", {"title": unique_name("tc"), **customer})["id"]
    requirement = made(
        "/api/requirements", {"title": unique_name("req"), "req_origin": "Customer"}
    )["id"]
    defect = made("/api/defects", {"title": unique_name("def"), **customer})["id"]
    suite = made("/api/test-suites", {"name": unique_name("ts"), **customer})["id"]
    campaign = made(
        "/api/campaigns", {"name": unique_name("cmp"), "test_case_ids": [case], **customer}
    )
    document = made(f"/api/projects/{project}/documents", {"title": unique_name("doc"), **customer})
    section = api_client.post(
        f"/api/documents/{document['id']}/sections", headers=admin, json={"title": "Scope"}
    ).json()["id"]
    headers = _external_author(api_client, admin, project)

    item = campaign["items"][0]["id"]
    attempts = [
        ("patch", f"/api/test-cases/{case}", {"title": "x"}),
        ("delete", f"/api/test-cases/{case}", None),
        ("post", f"/api/requirements/{requirement}/link-testrun", {"test_run_id": 1}),
        ("patch", f"/api/defects/{defect}", {"title": "x"}),
        ("post", f"/api/defects/{defect}/refresh-external", None),
        ("post", f"/api/test-suites/{suite}/items?test_case_id={case}", None),
        ("delete", f"/api/test-suites/{suite}", None),
        ("patch", f"/api/campaigns/{campaign['id']}", {"name": "x"}),
        ("patch", f"/api/campaigns/{campaign['id']}/items/{item}", {"comment": "x"}),
        ("delete", f"/api/campaigns/{campaign['id']}/items/{item}", None),
        ("patch", f"/api/documents/{document['id']}", {"title": "x"}),
        ("post", f"/api/documents/{document['id']}/sections", {"title": "x"}),
        ("patch", f"/api/document-sections/{section}", {"title": "x"}),
        ("delete", f"/api/document-sections/{section}", None),
    ]
    for method, path, body in attempts:
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        response = getattr(api_client, method)(path, **kwargs)
        assert response.status_code == 403, (method, path, response.status_code, response.text)
        detail = response.json()["detail"]
        if method == "delete" and detail.startswith("Missing permission: delete on "):
            continue
        assert detail == "External users change only what they created."
    uploaded = api_client.post(
        f"/api/documents/{document['id']}/attachments",
        headers=headers,
        files={"file": ("a.txt", b"x", "text/plain")},
    )
    assert uploaded.status_code == 403, uploaded.text


def test_a_type_outside_the_allowlist_answers_404_before_a_missing_right(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Allowlist first")["id"]
    design = api_client.post(
        "/api/designs",
        headers=admin,
        json={"project_id": project, "title": unique_name("des"), "visibility": "customer"},
    ).json()["id"]
    headers = _external_on(api_client, admin, project, "External Reader")

    edited = api_client.patch(f"/api/designs/{design}", headers=headers, json={"title": "x"})
    assert edited.status_code == 404, edited.text


def test_design_requests_check_creator_scope_and_external_review_authority(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Moves")["id"]
    others = api_client.post(
        "/api/designs",
        headers=admin,
        json={"project_id": project, "title": unique_name("des"), "visibility": "customer"},
    ).json()["id"]
    hidden = _create(api_client, admin, "designs", project).json()["id"]
    user = _create_user(api_client, admin, role="external")
    _grant(api_client, admin, "Design Author", user["id"], project)
    headers = _headers_for(api_client, user["email"])
    own = _create(api_client, headers, "designs", project).json()["id"]

    def request(design, as_headers=headers):
        return api_client.post(
            f"/api/artefacts/design/{design}/requests",
            headers=as_headers,
            json={"kind": "review"},
        )

    assert request(hidden).status_code == 404
    refused = request(others)
    assert refused.status_code == 403, refused.text
    assert refused.json()["detail"] == "Only the current revision's creator requests review."
    path = f"/api/artefacts/design/{own}"
    bypass = api_client.post(path + "/transition", headers=admin, json={"status": "Review"})
    assert bypass.status_code == 409, bypass.text
    to_review = request(own)
    assert to_review.status_code == 201, to_review.text
    denied = api_client.post(path + "/comments", headers=headers, json={"body": "Not eligible"})
    assert denied.status_code == 403, denied.text
    _grant(api_client, admin, "Approver", user["id"], project)
    unassigned = api_client.post(path + "/comments", headers=headers, json={"body": "Unassigned"})
    assert unassigned.status_code == 403, unassigned.text
    assigned = api_client.put(
        path + "/workflow/assignees", headers=admin, json={"reviewer_id": user["id"]}
    )
    assert assigned.status_code == 200, assigned.text
    reviewed = api_client.post(path + "/comments", headers=headers, json={"body": "Reviewed"})
    assert reviewed.status_code == 201, reviewed.text
    approval = api_client.post(path + "/requests", headers=headers, json={"kind": "approval"})
    assert approval.status_code == 201, approval.text
    denied_approval = api_client.post(path + "/sign-off", headers=headers, json={"step": "approve"})
    assert denied_approval.status_code == 403, denied_approval.text
    permissions = api_client.get(f"/api/projects/{project}/permissions", headers=headers)
    assert permissions.status_code == 200, permissions.text
    assert "review" in permissions.json()["DES"]
    assert not {"approve", "delete"} & set(permissions.json()["DES"])


def test_the_detail_read_names_the_changes_the_reader_may_make(api_client: TestClient):
    admin = _admin_headers(api_client)
    created = create_project(api_client, admin, "Answers")
    project, prefix = created["id"], created["prefix"]
    others = api_client.post(
        "/api/designs",
        headers=admin,
        json={"project_id": project, "title": unique_name("des"), "visibility": "customer"},
    ).json()
    hidden = _create(api_client, admin, "designs", project).json()
    user = _create_user(api_client, admin, role="external")
    _grant(api_client, admin, "Design Author", user["id"], project)
    headers = _headers_for(api_client, user["email"])
    own = _create(api_client, headers, "designs", project).json()
    reader = _external_on(api_client, admin, project, "External Reader")

    def actions(design, as_headers):
        response = api_client.get(
            f"/api/projects/{prefix}/docs/designs/{design['design_id']}", headers=as_headers
        )
        return response.status_code, response.json().get("allowed_actions")

    assert actions(others, admin) == (200, ["edit", "delete", "plan", "review", "approve"])
    assert actions(own, headers) == (200, ["edit"])
    assert actions(others, headers) == (200, [])
    assert actions(hidden, headers)[0] == 404
    assert actions(others, reader)[0] == 404


@pytest.mark.usefixtures("many_imports")
def test_an_external_import_creates_customer_rows_and_touches_only_its_own(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "External import")["id"]
    theirs = api_client.post(
        "/api/test-cases",
        headers=admin,
        json={"project_id": project, "title": unique_name("tc"), "visibility": "customer"},
    ).json()
    api_client.post(
        "/api/test-suites",
        headers=admin,
        json={"project_id": project, "name": "Boot", "visibility": "customer"},
    )
    headers = _external_author(api_client, admin, project)

    content = (
        "tc_id,title,visibility,status\n"
        f"{theirs['tc_id']},Taken,,\n"
        ",Mine,,\n"
        ",Inside,internal,\n"
        ",Approved,,Approved\n"
    ).encode()
    rows = _upload(api_client, headers, project, "test-cases", "c.csv", content, format="csv")
    assert rows.status_code == 201, rows.text
    body = rows.json()
    assert (body["created"], body["updated"], body["skipped"]) == (1, 0, 3)
    assert body["errors"] == [
        "row 1: not permitted",
        "row 3: not permitted",
        "row 4: not permitted",
    ]
    mine = api_client.get(f"/api/test-cases?project_id={project}", headers=headers).json()
    created = [case for case in mine["items"] if case["title"] == "Mine"]
    assert [case["visibility"] for case in created] == ["customer"]

    export = (
        "<suite><sections><section><name>Boot</name><cases>"
        "<case><id>C9</id><title>Rail</title></case>"
        "</cases></section></sections></suite>"
    ).encode()
    railed = _upload(api_client, headers, project, "testrail", "t.xml", export, format="xml")
    assert railed.status_code == 201, railed.text
    assert railed.json()["created"] == 1
    assert railed.json()["errors"] == ["case C9: adding to suite Boot not permitted"]


def test_an_external_users_document_is_customer_and_a_draft(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "External documents")["id"]
    headers = _external_author(api_client, admin, project)

    created = api_client.post(
        f"/api/projects/{project}/documents",
        headers=headers,
        json={"project_id": project, "title": unique_name("doc")},
    )
    assert created.status_code == 201, created.text
    assert (created.json()["visibility"], created.json()["status"]) == ("customer", "Draft")
    refused = api_client.post(
        f"/api/projects/{project}/documents",
        headers=headers,
        json={"project_id": project, "title": unique_name("doc"), "visibility": "internal"},
    )
    assert refused.status_code == 403
    assert refused.json()["detail"] == "External users create customer artefacts only."


@pytest.mark.usefixtures("many_imports")
def test_a_copy_reqif_or_markdown_import_by_an_external_user_creates_customer_rows(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    source = create_project(api_client, admin, "Copied from")["id"]
    target = create_project(api_client, admin, "Copied to")["id"]
    case = api_client.post(
        "/api/test-cases",
        headers=admin,
        json={"project_id": source, "title": unique_name("tc"), "visibility": "customer"},
    ).json()["id"]
    user = _create_user(api_client, admin, role="external")
    for project in (source, target):
        for policy in ("Requirements Author", "Test Author"):
            _grant(api_client, admin, policy, user["id"], project)
    headers = _headers_for(api_client, user["email"])

    copied = api_client.post(
        f"/api/projects/{target}/import",
        headers=headers,
        json={"source_project_id": source, "doc_type": "TC", "doc_ids": [case]},
    )
    assert copied.status_code == 201, copied.text
    assert copied.json()["imported"] == 1
    reqif = _upload(api_client, headers, target, "reqif", "s.reqif", SAMPLE_REQIF)
    assert reqif.status_code == 201, reqif.text
    assert reqif.json()["imported"] == 2
    markdown = _upload(
        api_client,
        headers,
        target,
        "markdown",
        "d.md",
        f"## [REQ] {unique_name('r')}\nBody\n".encode(),
    )
    assert markdown.status_code == 201, markdown.text
    assert markdown.json()["artefacts_created"] == 1

    cases = api_client.get(f"/api/test-cases?project_id={target}", headers=admin).json()["items"]
    assert [(c["visibility"], c["status"]) for c in cases] == [("customer", "Draft")]
    requirements = api_client.get(f"/api/requirements?project_id={target}", headers=admin).json()[
        "items"
    ]
    assert len(requirements) == 3
    assert {(r["visibility"], r["req_origin"], r["status"]) for r in requirements} == {
        ("customer", "Customer", "Draft")
    }


def test_the_detail_read_follows_the_permissions_of_a_user_who_is_not_external(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    created = create_project(api_client, admin, "Internal answers")
    project, prefix = created["id"], created["prefix"]
    design = _create(api_client, admin, "designs", project).json()

    def actions(policy):
        user = _create_user(api_client, admin, role="maintainer")
        _grant(api_client, admin, policy, user["id"], project)
        response = api_client.get(
            f"/api/projects/{prefix}/docs/designs/{design['design_id']}",
            headers=_headers_for(api_client, user["email"]),
        )
        assert response.status_code == 200, response.text
        return response.json()["allowed_actions"]

    assert actions("Design Author") == ["edit", "delete"]
    assert actions("Read Only") == []


def _maintainer_on(api_client, admin, project, *policies):
    """A maintainer holding the policies on the project, with their id and headers."""
    user = _create_user(api_client, admin, role="maintainer")
    for policy in policies:
        _grant(api_client, admin, policy, user["id"], project)
    return user, _headers_for(api_client, user["email"])


def test_controlled_status_edits_require_handoffs_and_independent_signoff_rights(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Edit statuses")["id"]
    user, headers = _maintainer_on(
        api_client, admin, project, "Requirements Author", "Design Author"
    )
    requirement = _create(api_client, headers, "requirements", project).json()["id"]
    path = f"/api/artefacts/requirement/{requirement}"
    reviewer, reviewer_headers = _policy_user(
        api_client, admin, {"REQ": ["view", "review"]}, project, return_user=True
    )
    approver, approver_headers = _policy_user(
        api_client, admin, {"REQ": ["view", "approve"]}, project, return_user=True
    )
    refused = api_client.patch(
        f"/api/requirements/{requirement}", headers=headers, json={"status": "Approved"}
    )
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"] == "Use the document workflow for status changes."
    unchanged = api_client.get(f"/api/requirements/{requirement}", headers=admin)
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["status"] == "Draft"
    invalid = api_client.put(
        path + "/workflow/assignees", headers=admin, json={"reviewer_id": user["id"]}
    )
    assert invalid.status_code == 422, invalid.text
    assigned = api_client.put(
        path + "/workflow/assignees",
        headers=admin,
        json={"reviewer_id": reviewer["id"], "approver_id": approver["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    requested = api_client.post(path + "/requests", headers=headers, json={"kind": "review"})
    assert requested.status_code == 201, requested.text
    unauthorized = api_client.post(path + "/sign-off", headers=headers, json={"step": "review"})
    assert unauthorized.status_code == 403, unauthorized.text
    comment = api_client.post(
        path + "/comments", headers=reviewer_headers, json={"body": "Reviewed requested content"}
    )
    assert comment.status_code == 201, comment.text
    approval = api_client.post(
        path + "/requests", headers=reviewer_headers, json={"kind": "approval"}
    )
    assert approval.status_code == 201, approval.text
    for as_headers in (headers, reviewer_headers):
        denied = api_client.post(path + "/sign-off", headers=as_headers, json={"step": "approve"})
        assert denied.status_code == 403, denied.text
    approved = api_client.post(
        path + "/sign-off", headers=approver_headers, json={"step": "approve"}
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["reviewed_by_id"] == reviewer["id"]
    assert approved.json()["approved_by_id"] == approver["id"]
    stored = api_client.get(f"/api/requirements/{requirement}", headers=admin)
    assert stored.status_code == 200, stored.text
    assert stored.json()["status"] == "Approved"
    permissions = api_client.get(f"/api/projects/{project}/permissions", headers=reviewer_headers)
    assert permissions.status_code == 200, permissions.text
    assert "review" in permissions.json()["REQ"]
    assert not {"create", "edit", "approve", "delete"} & set(permissions.json()["REQ"])

    document = api_client.post(
        f"/api/projects/{project}/documents",
        headers=admin,
        json={"project_id": project, "title": unique_name("doc")},
    )
    assert document.status_code == 201, document.text
    _, reader_headers = _maintainer_on(api_client, admin, project, "Requirements Author")
    refused = api_client.patch(
        f"/api/documents/{document.json()['id']}",
        headers=reader_headers,
        json={"status": "Approved"},
    )
    assert refused.status_code == 409, refused.text
    defect = _create(api_client, admin, "defects", project).json()["id"]
    design = _create(api_client, admin, "designs", project).json()["id"]
    _, author_headers = _maintainer_on(api_client, admin, project, "Design Author")
    refused = api_client.patch(
        f"/api/defects/{defect}", headers=author_headers, json={"status": "Rejected"}
    )
    assert refused.status_code == 403, refused.text
    assert refused.json()["detail"] == "Missing permission: approve on DEF."
    refused = api_client.patch(
        f"/api/designs/{design}", headers=author_headers, json={"status": "Approved"}
    )
    assert refused.status_code == 409, refused.text


def test_controlled_creation_stays_draft_with_or_without_approve(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Created approved")["id"]
    author, headers = _maintainer_on(api_client, admin, project, "Requirements Author")

    def create(as_headers, status):
        return api_client.post(
            "/api/requirements",
            headers=as_headers,
            json={"project_id": project, "title": unique_name("req"), "status": status},
        )

    created = create(headers, "Draft")
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "Draft"
    for as_headers in (headers, admin):
        for status in ("Review", "Approved", "Rejected"):
            refused = create(as_headers, status)
            assert refused.status_code == 422, refused.text
            assert refused.json()["detail"] == "New controlled documents start in Draft."
    _grant(api_client, admin, "Approver", author["id"], project)
    permissions = api_client.get(f"/api/projects/{project}/permissions", headers=headers)
    assert permissions.status_code == 200, permissions.text
    assert "approve" in permissions.json()["REQ"]
    refused = create(headers, "Approved")
    assert refused.status_code == 422, refused.text
    _, reader = _maintainer_on(api_client, admin, project, "Read Only")
    refused = create(reader, "Draft")
    assert refused.status_code == 403, refused.text
    assert refused.json()["detail"] == "Missing permission: create on REQ."


def test_a_sign_off_records_the_actor_of_the_actual_assigned_handoff(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Signed")["id"]
    requirement = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": unique_name("req"), "req_origin": "Customer"},
    ).json()["id"]
    hidden = _create(api_client, admin, "requirements", project).json()["id"]
    design = _create(api_client, admin, "designs", project).json()["id"]
    approver, approver_headers = _maintainer_on(api_client, admin, project, "Approver")
    _, author_headers = _maintainer_on(api_client, admin, project, "Requirements Author")
    external = _external_on(api_client, admin, project, "Approver")
    path = f"/api/artefacts/requirement/{requirement}"

    def sign(as_headers, kind, item, step):
        return api_client.post(
            f"/api/artefacts/{kind}/{item}/sign-off", headers=as_headers, json={"step": step}
        )

    unassigned = sign(approver_headers, "requirement", requirement, "review")
    assert unassigned.status_code == 403, unassigned.text
    assigned = api_client.put(
        path + "/workflow/assignees",
        headers=admin,
        json={"reviewer_id": approver["id"], "approver_id": approver["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    request = api_client.post(path + "/requests", headers=admin, json={"kind": "review"})
    assert request.status_code == 201, request.text
    missing_comment = sign(approver_headers, "requirement", requirement, "review")
    assert missing_comment.status_code == 409, missing_comment.text
    assert sign(author_headers, "requirement", requirement, "review").status_code == 403
    comment = api_client.post(
        path + "/comments", headers=approver_headers, json={"body": "Reviewed request content"}
    )
    assert comment.status_code == 201, comment.text
    reviewed = sign(approver_headers, "requirement", requirement, "review")
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["reviewed_by_id"] == approver["id"]
    refused = sign(external, "requirement", requirement, "approve")
    assert refused.status_code == 403, refused.text
    permissions = api_client.get(f"/api/projects/{project}/permissions", headers=external)
    assert permissions.status_code == 200, permissions.text
    assert "review" in permissions.json()["REQ"]
    assert not {"approve", "delete"} & set(permissions.json()["REQ"])
    approved = sign(approver_headers, "requirement", requirement, "approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["approved_by_id"] == approver["id"]
    stored = api_client.get(f"/api/requirements/{requirement}", headers=admin).json()
    assert (stored["reviewed_by_id"], stored["approved_by_id"]) == (approver["id"], approver["id"])
    assert stored["status"] == "Approved"
    assert sign(external, "requirement", hidden, "review").status_code == 404
    refused = sign(approver_headers, "design", design, "review")
    assert refused.status_code == 403, refused.text
    assert refused.json()["detail"] == "Only the assigned reviewer requests approval."
    assert sign(approver_headers, "requirement", requirement, "sign").status_code == 422


@pytest.mark.parametrize("grant_approve", [False, True])
@pytest.mark.usefixtures("many_imports")
def test_import_statuses_cannot_skip_controlled_handoffs(api_client: TestClient, grant_approve):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Imported statuses")["id"]
    existing = _create(api_client, admin, "test-cases", project).json()
    content = (
        "tc_id,title,status\n"
        f"{existing['tc_id']},Bypassed,Approved\n"
        ",Approved new,Approved\n"
        ",In review,Review\n"
        ",Draft new,Draft\n"
        f"{existing['tc_id']},Draft edit,Draft\n"
    ).encode()
    actions = ["view", "import", "create", "edit"]
    if grant_approve:
        actions += ["review", "approve"]
    writer = _policy_user(api_client, admin, {"TC": actions}, project)
    imported = _upload(api_client, writer, project, "test-cases", "c.csv", content, format="csv")
    assert imported.status_code == 201, imported.text
    body = imported.json()
    assert (body["created"], body["updated"], body["skipped"]) == (1, 1, 3)
    assert body["errors"] == [
        "row 1: not permitted",
        "row 2: not permitted",
        "row 3: not permitted",
    ]
    stored = api_client.get(f"/api/test-cases/{existing['id']}", headers=admin)
    assert stored.status_code == 200, stored.text
    assert (stored.json()["title"], stored.json()["status"]) == ("Draft edit", "Draft")
    rows = api_client.get(f"/api/test-cases?project_id={project}", headers=admin)
    assert rows.status_code == 200, rows.text
    assert sorted((row["title"], row["status"]) for row in rows.json()["items"]) == [
        ("Draft edit", "Draft"),
        ("Draft new", "Draft"),
    ]


def test_controlled_case_and_suite_use_handoffs_while_campaign_keeps_its_rights(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "More statuses")["id"]
    _, headers = _maintainer_on(api_client, admin, project, "Test Author")
    signer, signer_headers = _maintainer_on(api_client, admin, project, "Approver")
    case = _create(api_client, headers, "test-cases", project).json()["id"]
    suite = api_client.post(
        "/api/test-suites", headers=headers, json={"project_id": project, "name": unique_name("s")}
    )
    assert suite.status_code == 201, suite.text
    campaign = api_client.post(
        "/api/campaigns", headers=headers, json={"project_id": project, "name": unique_name("c")}
    )
    assert campaign.status_code == 201, campaign.text

    for slug, route, item in (
        ("test-case", "test-cases", case),
        ("test-suite", "test-suites", suite.json()["id"]),
    ):
        refused = api_client.patch(
            f"/api/{route}/{item}", headers=headers, json={"status": "Approved"}
        )
        assert refused.status_code == 409, refused.text
        path = f"/api/artefacts/{slug}/{item}"
        assigned = api_client.put(
            path + "/workflow/assignees",
            headers=admin,
            json={"reviewer_id": signer["id"], "approver_id": signer["id"]},
        )
        assert assigned.status_code == 200, assigned.text
        requested = api_client.post(path + "/requests", headers=headers, json={"kind": "review"})
        assert requested.status_code == 201, requested.text
        comment = api_client.post(
            path + "/comments", headers=signer_headers, json={"body": "Reviewed"}
        )
        assert comment.status_code == 201, comment.text
        approval = api_client.post(
            path + "/requests", headers=signer_headers, json={"kind": "approval"}
        )
        assert approval.status_code == 201, approval.text
        refused = api_client.post(path + "/sign-off", headers=headers, json={"step": "approve"})
        assert refused.status_code == 403, refused.text
        approved = api_client.post(
            path + "/sign-off", headers=signer_headers, json={"step": "approve"}
        )
        assert approved.status_code == 200, approved.text
        stored = api_client.get(f"/api/{route}/{item}", headers=admin)
        assert stored.status_code == 200, stored.text
        assert stored.json()["status"] == "Approved"

    path = f"/api/campaigns/{campaign.json()['id']}"
    moved = api_client.patch(path, headers=headers, json={"status": "In Progress"})
    assert moved.status_code == 200, moved.text
    refused = api_client.patch(path, headers=headers, json={"status": "Approved"})
    assert refused.status_code == 403, refused.text
    assert refused.json()["detail"] == "Missing permission: approve on CMP."


@pytest.mark.usefixtures("many_imports")
def test_new_import_rows_start_draft_and_create_does_not_grant_edit(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Create-only import")["id"]
    existing = _create(api_client, admin, "test-cases", project).json()
    creator = _policy_user(api_client, admin, {"TC": ["view", "import", "create"]}, project)
    content = (
        "tc_id,title,status\n"
        f"{existing['tc_id']},No edit,Draft\n"
        ",Under review,Review\n"
        ",Signed,Approved\n"
        ",Draft new,Draft\n"
    ).encode()
    imported = _upload(api_client, creator, project, "test-cases", "c.csv", content, format="csv")
    assert imported.status_code == 201, imported.text
    body = imported.json()
    assert (body["created"], body["updated"], body["skipped"]) == (1, 0, 3)
    assert body["errors"] == [
        "row 1: not permitted",
        "row 2: not permitted",
        "row 3: not permitted",
    ]
    stored = api_client.get(f"/api/test-cases/{existing['id']}", headers=admin)
    assert stored.status_code == 200, stored.text
    assert (stored.json()["title"], stored.json()["status"]) == (existing["title"], "Draft")
    rows = api_client.get(f"/api/test-cases?project_id={project}", headers=admin)
    assert rows.status_code == 200, rows.text
    assert {(row["title"], row["status"]) for row in rows.json()["items"]} == {
        (existing["title"], "Draft"),
        ("Draft new", "Draft"),
    }


def _scoped_external(api_client, admin, project, permissions, scope):
    """An external user whose policy grants the permissions on the project's chosen types."""
    return _policy_user(api_client, admin, permissions, project, role="external", scope=scope)


def _link(api_client, headers, project, source, target, role="verifies"):
    """Ask for a link between two (type, id) ends."""
    return api_client.post(
        "/api/links",
        headers=headers,
        json={
            "project_id": project,
            "source_type": source[0],
            "source_id": source[1],
            "target_type": target[0],
            "target_id": target[1],
            "role": role,
        },
    )


def test_a_link_needs_both_ends_visible_and_an_external_users_own_ends(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Linked")["id"]
    customer = {"req_origin": "Customer"}
    theirs = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": unique_name("req"), **customer},
    ).json()["id"]
    hidden = _create(api_client, admin, "requirements", project).json()["id"]
    design = api_client.post(
        "/api/designs",
        headers=admin,
        json={"project_id": project, "title": unique_name("des"), "visibility": "customer"},
    ).json()["id"]
    writes = ["view", "comment", "create", "edit", "delete"]
    headers = _scoped_external(
        api_client,
        admin,
        project,
        {"REQ": writes, "TC": writes, "DES": ["view"], "link": writes},
        ["REQ", "TC"],
    )
    own_req = _create(api_client, headers, "requirements", project).json()["id"]
    own_case = _create(api_client, headers, "test-cases", project).json()["id"]

    assert (
        _link(api_client, headers, project, ("TC", own_case), ("REQ", own_req)).status_code == 201
    )
    refused = _link(api_client, headers, project, ("TC", own_case), ("REQ", theirs))
    assert refused.status_code == 403
    assert refused.json()["detail"] == "External users change only what they created."
    unknown = _link(api_client, headers, project, ("TC", own_case), ("REQ", hidden))
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "Target document not found in project"
    outside = _link(api_client, headers, project, ("DES", design), ("REQ", own_req), "references")
    assert outside.status_code == 404
    assert outside.json()["detail"] == "Source document not found in project"


def test_a_link_with_a_hidden_end_is_hidden_and_one_with_a_deleted_end_can_go(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Unlinked")["id"]
    customer_case = api_client.post(
        "/api/test-cases",
        headers=admin,
        json={"project_id": project, "title": unique_name("tc"), "visibility": "customer"},
    ).json()["id"]
    customer_req = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": unique_name("req"), "req_origin": "Customer"},
    ).json()["id"]
    hidden_req = _create(api_client, admin, "requirements", project).json()["id"]
    gone_req = _create(api_client, admin, "requirements", project).json()["id"]

    def made(target):
        response = _link(api_client, admin, project, ("TC", customer_case), ("REQ", target))
        assert response.status_code == 201, response.text
        return response.json()["id"]

    shown_link, hidden_link, orphan_link = made(customer_req), made(hidden_req), made(gone_req)
    assert api_client.delete(f"/api/requirements/{gone_req}", headers=admin).status_code == 204
    external = _external_on(api_client, admin, project, "Test Author", "Requirements Author")
    _, maintainer = _maintainer_on(api_client, admin, project, "Test Author")

    refused = api_client.delete(f"/api/links/{shown_link}", headers=external)
    assert refused.status_code == 403
    assert api_client.delete(f"/api/links/{hidden_link}", headers=external).status_code == 404
    assert api_client.delete(f"/api/links/{orphan_link}", headers=maintainer).status_code == 204


def test_a_tag_links_only_to_a_visible_artefact_of_the_same_project(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Tagged")["id"]
    other = create_project(api_client, admin, "Elsewhere")["id"]
    shown = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": unique_name("req"), "req_origin": "Customer"},
    ).json()["id"]
    hidden = _create(api_client, admin, "requirements", project).json()["id"]
    elsewhere = _create(api_client, admin, "requirements", other).json()["id"]
    headers = _external_on(api_client, admin, project, "Requirements Author")

    def tag(item):
        return {
            "type": "mention",
            "attrs": {"id": f"REQ:{item}", "label": "x", "mentionSuggestionChar": "#"},
        }

    body = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [tag(shown), tag(hidden), tag(elsewhere), tag(999999)]}
        ],
    }
    created = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project, "title": unique_name("req"), "content_json": body},
    )
    assert created.status_code == 201, created.text
    links = api_client.get(
        f"/api/links?project_id={project}&source_type=REQ&source_id={created.json()['id']}",
        headers=admin,
    ).json()
    assert [(link["target_type"], link["target_id"]) for link in links] == [("REQ", shown)]


@pytest.mark.usefixtures("many_imports")
def test_an_external_import_links_only_between_rows_the_importer_created(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Imported links")["id"]
    theirs = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": unique_name("req"), "req_origin": "Customer"},
    ).json()["req_id"]
    headers = _external_on(api_client, admin, project, "Test Author", "Requirements Author")
    export = (
        "<suite><sections><section><name>Rail</name><cases><case><id>C7</id>"
        f"<title>Linked</title><references>{theirs}</references>"
        "</case></cases></section></sections></suite>"
    ).encode()

    railed = _upload(api_client, headers, project, "testrail", "t.xml", export, format="xml")
    assert railed.status_code == 201, railed.text
    assert railed.json()["links_created"] == 0
    assert railed.json()["errors"] == ["case C7: links not permitted"]

    unrelated = re.sub(
        rb"<SPEC-RELATION IDENTIFIER=\"REL-1\">.*?</SPEC-RELATION>", b"", SAMPLE_REQIF, flags=re.S
    )
    imported = _upload(api_client, admin, project, "reqif", "s.reqif", unrelated)
    assert imported.status_code == 201, imported.text
    assert imported.json()["links_created"] == 0
    for item in api_client.get(f"/api/requirements?project_id={project}", headers=admin).json()[
        "items"
    ]:
        api_client.patch(
            f"/api/requirements/{item['id']}", headers=admin, json={"req_origin": "Customer"}
        )
    again = _upload(api_client, headers, project, "reqif", "s.reqif", SAMPLE_REQIF)
    assert again.status_code == 201, again.text
    assert again.json()["links_created"] == 0
    assert again.json()["errors"] == ["relation REL-1: not permitted"]


def test_a_hidden_link_is_not_found_before_a_missing_delete_right(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Unseen links")["id"]
    case = api_client.post(
        "/api/test-cases",
        headers=admin,
        json={"project_id": project, "title": unique_name("tc"), "visibility": "customer"},
    ).json()["id"]
    shown = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": unique_name("req"), "req_origin": "Customer"},
    ).json()["id"]
    hidden = _create(api_client, admin, "requirements", project).json()["id"]
    shown_link = _link(api_client, admin, project, ("TC", case), ("REQ", shown)).json()["id"]
    hidden_link = _link(api_client, admin, project, ("TC", case), ("REQ", hidden)).json()["id"]
    reader = _external_on(api_client, admin, project, "External Reader")

    assert api_client.delete(f"/api/links/{hidden_link}", headers=reader).status_code == 404
    refused = api_client.delete(f"/api/links/{shown_link}", headers=reader)
    assert refused.status_code == 403
    assert refused.json()["detail"] == "Missing permission: delete on link."


def test_a_read_by_id_needs_the_view_right_on_the_type(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Viewed by id")["id"]
    requirement = _create(api_client, admin, "requirements", project).json()["id"]
    blind = _policy_user(api_client, admin, {"REQ": ["comment"]}, project)
    seeing = _policy_user(api_client, admin, {"REQ": ["view"]}, project)

    for path in (
        f"/api/requirements/{requirement}",
        f"/api/requirements/{requirement}/test-runs",
        f"/api/artefacts/requirement/{requirement}/comments",
        f"/api/artefacts/requirement/{requirement}/activity",
        f"/api/artefacts/requirement/{requirement}/related",
    ):
        assert api_client.get(path, headers=blind).status_code == 404, path
        assert api_client.get(path, headers=seeing).status_code == 200, path


def test_commenting_requires_selected_review_visibility_and_assignment(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Commented")["id"]
    requirement = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": unique_name("req"), "req_origin": "Customer"},
    ).json()["id"]
    _, reader = _maintainer_on(api_client, admin, project, "Read Only")
    external = _external_on(api_client, admin, project, "External Reader")
    path = f"/api/artefacts/requirement/{requirement}"
    for headers in (reader, external):
        refused = api_client.post(path + "/comments", headers=headers, json={"body": "Read only"})
        assert refused.status_code == 403, refused.text
        assert refused.json()["detail"] == "Only the assigned reviewer may comment."
    reviewer, reviewer_headers = _policy_user(
        api_client,
        admin,
        {"REQ": ["review"]},
        project,
        role="external",
        scope=["REQ"],
        return_user=True,
    )
    blind = api_client.get(f"/api/requirements/{requirement}", headers=reviewer_headers)
    assert blind.status_code == 404, blind.text
    invalid = api_client.put(
        path + "/workflow/assignees", headers=admin, json={"reviewer_id": reviewer["id"]}
    )
    assert invalid.status_code == 422, invalid.text
    _grant(api_client, admin, "External Reader", reviewer["id"], project)
    seeing = api_client.get(f"/api/requirements/{requirement}", headers=reviewer_headers)
    assert seeing.status_code == 200, seeing.text
    unassigned = api_client.post(
        path + "/comments", headers=reviewer_headers, json={"body": "Not assigned"}
    )
    assert unassigned.status_code == 403, unassigned.text
    assigned = api_client.put(
        path + "/workflow/assignees", headers=admin, json={"reviewer_id": reviewer["id"]}
    )
    assert assigned.status_code == 200, assigned.text
    comment = api_client.post(
        path + "/comments", headers=reviewer_headers, json={"body": "Assigned customer review"}
    )
    assert comment.status_code == 201, comment.text
    assert comment.json()["author_user_id"] == reviewer["id"]
    permissions = api_client.get(f"/api/projects/{project}/permissions", headers=reviewer_headers)
    assert permissions.status_code == 200, permissions.text
    assert {"view", "review"} <= set(permissions.json()["REQ"])
    assert not {"create", "edit", "approve", "delete"} & set(permissions.json()["REQ"])


def test_a_reviewer_or_approver_must_see_the_artefact_and_hold_the_right(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Assigned")["id"]
    approver, _ = _maintainer_on(api_client, admin, project, "Approver")
    author, _ = _maintainer_on(api_client, admin, project, "Requirements Author")
    outsider = _create_user(api_client, admin, role="maintainer")
    external = _create_user(api_client, admin, role="external")
    _grant(api_client, admin, "Approver", external["id"], project)

    def create(path, **assignees):
        body = {"project_id": project, "title": unique_name("x"), **assignees}
        return api_client.post(path, headers=admin, json=body)

    assert create("/api/requirements", reviewer_id=approver["id"]).status_code == 201
    for user in (author, outsider, external):
        refused = create("/api/requirements", reviewer_id=user["id"])
        assert refused.status_code == 422, user
        assert "cannot see" in refused.json()["detail"]
    assert create("/api/test-cases", approver_id=external["id"]).status_code == 422
    assert create("/api/defects", reviewer_id=external["id"]).status_code == 422
    requirement = create("/api/requirements").json()["id"]
    edited = api_client.patch(
        f"/api/requirements/{requirement}", headers=admin, json={"approver_id": author["id"]}
    )
    assert edited.status_code == 422


def test_what_a_user_cannot_view_they_cannot_change(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Unseen changes")["id"]
    requirement = _create(api_client, admin, "requirements", project).json()["id"]
    case = _create(api_client, admin, "test-cases", project).json()["id"]
    writes = ["create", "edit", "delete", "comment"]
    blind = _policy_user(
        api_client,
        admin,
        {"REQ": writes, "TC": ["view", *writes], "link": ["view", "create"]},
        project,
        scope=["TC"],
    )

    edited = api_client.patch(
        f"/api/requirements/{requirement}", headers=blind, json={"title": "x"}
    )
    assert edited.status_code == 404
    commented = api_client.post(
        f"/api/artefacts/requirement/{requirement}/comments", headers=blind, json={"body": "x"}
    )
    assert commented.status_code == 404
    linked = _link(api_client, blind, project, ("TC", case), ("REQ", requirement))
    assert linked.status_code == 404
    assert api_client.delete(f"/api/requirements/{requirement}", headers=blind).status_code == 404


LIST_KINDS = {
    "requirements": ("REQ", "title"),
    "test-cases": ("TC", "title"),
    "test-suites": ("TS", "name"),
    "campaigns": ("CMP", "name"),
    "defects": ("DEF", "title"),
    "designs": ("DES", "title"),
    "risks": ("RSK", "title"),
    "changes": ("CHG", "title"),
    "test-concepts": ("CPT", "name"),
}


def _rows(body) -> list:
    """The rows of a list answer, paged or plain."""
    return body["items"] if isinstance(body, dict) else body


def test_a_list_of_a_type_without_view_is_empty(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Listed")["id"]
    for kind, (_, field) in LIST_KINDS.items():
        created = api_client.post(
            f"/api/{kind}", headers=admin, json={"project_id": project, field: unique_name(kind)}
        )
        assert created.status_code == 201, (kind, created.text)
    blind = _policy_user(api_client, admin, {"link": ["view"]}, project)
    seeing = _policy_user(
        api_client, admin, {code: ["view"] for code, _ in LIST_KINDS.values()}, project
    )

    for kind in LIST_KINDS:
        hidden = api_client.get(f"/api/{kind}", headers=blind, params={"project_id": project})
        assert hidden.status_code == 200, (kind, hidden.text)
        assert _rows(hidden.json()) == [], kind
        shown = api_client.get(f"/api/{kind}", headers=seeing, params={"project_id": project})
        assert len(_rows(shown.json())) == 1, kind


def test_the_registry_and_type_summary_leave_out_a_type_without_view(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Registry")["id"]
    requirement = _create(api_client, admin, "requirements", project).json()
    case = _create(api_client, admin, "test-cases", project).json()["id"]
    assert (
        _link(api_client, admin, project, ("TC", case), ("REQ", requirement["id"])).status_code
        == 201
    )
    campaign = api_client.post(
        "/api/campaigns",
        headers=admin,
        json={"project_id": project, "name": unique_name("cmp"), "test_case_ids": [case]},
    )
    assert campaign.status_code == 201, campaign.text
    reader = _policy_user(api_client, admin, {"REQ": ["view"], "CMP": ["view"]}, project)

    docs = api_client.get(f"/api/projects/{project}/docs", headers=reader).json()["items"]
    assert sorted(doc["doc_type"] for doc in docs) == ["CMP", "REQ"]
    assert all(doc["incoming_links"] == doc["outgoing_links"] == 0 for doc in docs)
    summary = api_client.get(f"/api/projects/{project}/doc-type-summary", headers=reader).json()
    assert sorted(entry["doc_type"] for entry in summary["types"]) == ["CMP", "REQ"]
    assert summary["membership_edges"] == []
    detail = api_client.get(
        f"/api/projects/{project}/docs/requirements/{requirement['req_id']}", headers=reader
    ).json()
    assert detail["incoming_links"] == 0
    admin_detail = api_client.get(
        f"/api/projects/{project}/docs/requirements/{requirement['req_id']}", headers=admin
    ).json()
    assert admin_detail["incoming_links"] == 1
    hidden = api_client.get(f"/api/projects/{project}/next-doc-id/TC", headers=reader)
    unknown = api_client.get(f"/api/projects/{project}/next-doc-id/XYZ", headers=reader)
    assert hidden.status_code == unknown.status_code == 400
    assert hidden.json()["detail"] == "Unsupported document type: TC"


def test_the_link_list_leaves_out_links_with_an_end_of_a_type_without_view(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Linked list")["id"]
    requirement = _create(api_client, admin, "requirements", project).json()["id"]
    case = _create(api_client, admin, "test-cases", project).json()["id"]
    assert _link(api_client, admin, project, ("TC", case), ("REQ", requirement)).status_code == 201
    partial = _policy_user(api_client, admin, {"REQ": ["view"], "link": ["view"]}, project)
    both = _policy_user(
        api_client, admin, {"REQ": ["view"], "TC": ["view"], "link": ["view"]}, project
    )

    params = {"project_id": project}
    assert api_client.get("/api/links", headers=partial, params=params).json() == []
    assert len(api_client.get("/api/links", headers=both, params=params).json()) == 1


def test_nested_rows_and_counts_follow_the_view_right(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Nested")["id"]
    requirement = _create(api_client, admin, "requirements", project).json()["id"]
    case = _create(api_client, admin, "test-cases", project).json()["id"]
    assert _link(api_client, admin, project, ("TC", case), ("REQ", requirement)).status_code == 201
    campaign = api_client.post(
        "/api/campaigns",
        headers=admin,
        json={"project_id": project, "name": unique_name("cmp"), "test_case_ids": [case]},
    ).json()["id"]
    reader = _policy_user(api_client, admin, {"REQ": ["view"], "CMP": ["view"]}, project)

    detail = api_client.get(f"/api/requirements/{requirement}", headers=reader).json()
    assert detail["linked_test_cases"] == []
    assert detail["test_case_count"] == 0
    row = _rows(
        api_client.get("/api/requirements", headers=reader, params={"project_id": project}).json()
    )[0]
    assert row["test_case_count"] == 0
    campaign_detail = api_client.get(f"/api/campaigns/{campaign}", headers=reader).json()
    assert campaign_detail["items"] == []
    assert campaign_detail["total_items"] == 0
    admin_detail = api_client.get(f"/api/campaigns/{campaign}", headers=admin).json()
    assert admin_detail["total_items"] == 1


def test_search_dashboard_and_project_counts_leave_out_a_type_without_view(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Counted")["id"]
    word = unique_name("needle").replace(" ", "")
    for kind, customer in (("requirements", {"req_origin": "Customer"}), ("test-cases", {})):
        created = api_client.post(
            f"/api/{kind}",
            headers=admin,
            json={"project_id": project, "title": word, "visibility": "customer", **customer},
        )
        assert created.status_code == 201, created.text
    reader = _policy_user(api_client, admin, {"REQ": ["view"]}, project)
    external = _create_user(api_client, admin, role="external")
    added = add_policy_member(
        api_client,
        headers=admin,
        url=f"/api/projects/{project}/members",
        user_id=external["id"],
        permissions={"*": ["view", "comment"]},
        visibility="customer",
        doc_types=["REQ"],
    )
    assert added.status_code == 201, added.text
    external_headers = _headers_for(api_client, external["email"])

    counts = api_client.get(f"/api/projects/{project}", headers=reader).json()
    assert (counts["requirement_count"], counts["test_case_count"]) == (1, 0)
    found = api_client.get(
        "/api/search", headers=external_headers, params={"q": word, "project_id": project}
    ).json()
    assert [item["type"] for item in found["items"]] == ["REQ"]
    stats = api_client.get("/api/dashboard/stats", headers=external_headers).json()
    assert stats["total_requirements"] == 1
    assert stats["total_test_cases"] == 0


def test_traceability_follows_the_view_right(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Traced")["id"]
    requirement = _create(api_client, admin, "requirements", project).json()["id"]
    case = _create(api_client, admin, "test-cases", project).json()["id"]
    assert _link(api_client, admin, project, ("TC", case), ("REQ", requirement)).status_code == 201
    no_requirements = _policy_user(api_client, admin, {"TC": ["view"]}, project)
    no_test_cases = _policy_user(api_client, admin, {"REQ": ["view"]}, project)
    params = {"project_id": project}

    matrix = api_client.get("/api/traceability", headers=no_requirements, params=params).json()
    assert matrix["items"] == []
    gaps = api_client.get(f"/api/traceability/coverage-gaps/{project}", headers=no_requirements)
    assert gaps.json()["total_requirements"] == 0
    impact = api_client.get(f"/api/traceability/impact/{requirement}", headers=no_requirements)
    assert impact.status_code == 404

    matrix = api_client.get("/api/traceability", headers=no_test_cases, params=params).json()
    assert [item["linked_test_cases"] for item in matrix["items"]] == [[]]
    impact = api_client.get(f"/api/traceability/impact/{requirement}", headers=no_test_cases)
    assert impact.json()["root_requirement"]["test_case_count"] == 0


def test_an_export_leaves_out_types_without_view(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Exported")["id"]
    requirement = _create(api_client, admin, "requirements", project).json()["id"]
    case = _create(api_client, admin, "test-cases", project).json()
    assert (
        _link(api_client, admin, project, ("TC", case["id"]), ("REQ", requirement)).status_code
        == 201
    )
    exporter = _policy_user(
        api_client, admin, {"REQ": ["view", "export"], "TC": ["export"]}, project
    )

    cases = api_client.get(f"/api/projects/{project}/export/test-cases", headers=exporter)
    assert cases.status_code == 200
    assert cases.text.strip().count("\n") == 0
    trace = api_client.get(f"/api/projects/{project}/export/traceability", headers=exporter)
    assert trace.status_code == 200
    assert case["tc_id"] not in trace.text


def test_a_baseline_snapshot_shows_only_sections_of_visible_types(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Baselined")["id"]
    _create(api_client, admin, "requirements", project)
    baseline = api_client.post(
        "/api/baselines", headers=admin, json={"project_id": project, "name": unique_name("bl")}
    ).json()["id"]
    some = _policy_user(
        api_client, admin, {"REQ": ["view"], "SPEC": ["view"], "baseline": ["view"]}, project
    )
    documents = _policy_user(
        api_client,
        admin,
        {code: ["view"] for code in ("SPEC", "PRT", "RPT", "STD", "baseline")},
        project,
    )

    snapshot = api_client.get(f"/api/baselines/{baseline}", headers=some).json()["snapshot"]
    assert set(snapshot) == {"requirements"}
    snapshot = api_client.get(f"/api/baselines/{baseline}", headers=documents).json()["snapshot"]
    assert set(snapshot) == {"documents"}
    listed = api_client.get("/api/baselines", headers=some, params={"project_id": project})
    assert set(listed.json()[0]["snapshot"]) == {"requirements"}
    assert len(api_client.get(f"/api/baselines/{baseline}", headers=admin).json()["snapshot"]) == 6
