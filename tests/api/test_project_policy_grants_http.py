"""Group-owned policies and explicit project replacements enforce complete rules."""

from app.core.permissions import RESOURCE_ACTIONS
from tests.access_fixtures import scenario_rules
from tests.api.test_groups_http import _admin_headers, _create_user, _headers_for
from tests.conftest import create_project, unique_name


def _policy(client, headers, visibility="internal", permissions=None, types=None):
    response = client.post(
        "/api/policies",
        headers=headers,
        json={
            "name": unique_name("Scoped policy"),
            "rules": scenario_rules(permissions or {"REQ": ["view"]}, visibility, types),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_policy_contract_gives_rules_with_tags_and_omits_base_role(api_client):
    headers = _admin_headers(api_client)
    policy = _policy(api_client, headers, visibility="customer", types=["REQ"])
    expected = {
        "REQ": {
            "read": True,
            "write": False,
            "review": False,
            "approve": False,
            "delete": False,
            "all_origins": False,
            "visibility": ["customer"],
            "tags": [],
            "actions": ["comment", "view"],
        }
    }
    assert policy["rules"] == expected
    assert "base_role" not in policy
    copy = api_client.post(f"/api/policies/{policy['id']}/duplicate", headers=headers)
    assert copy.status_code == 201, copy.text
    assert copy.json()["rules"] == expected


def test_multiple_policies_are_applied_on_only_the_granted_project(api_client):
    headers = _admin_headers(api_client)
    user = _create_user(api_client, headers, role="maintainer")
    user_headers = _headers_for(api_client, user["email"])
    project = create_project(api_client, headers, "Assigned")["id"]
    other = create_project(api_client, headers, "Unassigned")["id"]
    read = _policy(api_client, headers, permissions={"REQ": ["view"]}, types=["REQ"])
    write = _policy(
        api_client, headers, permissions={"TC": ["view", "create", "edit"]}, types=["TC"]
    )
    group = api_client.post(
        "/api/groups",
        headers=headers,
        json={"name": unique_name("Team"), "policy_ids": [read["id"], write["id"]]},
    ).json()
    assert "policy_id" not in group
    member = api_client.post(
        f"/api/groups/{group['id']}/members", headers=headers, json={"user_id": user["id"]}
    )
    assert member.status_code == 201, member.text
    granted = api_client.post(
        f"/api/groups/{group['id']}/grants",
        headers=headers,
        json={"project_id": project},
    )
    assert granted.status_code == 201, granted.text
    grant = granted.json()["grants"][0]
    assert grant["project_id"] == project
    assert "policy_ids" not in grant
    assert set(granted.json()["policy_ids"]) == {read["id"], write["id"]}
    assert api_client.get(f"/api/projects/{project}", headers=user_headers).status_code == 200
    assert api_client.get(f"/api/projects/{other}", headers=user_headers).status_code == 403
    effective = api_client.get(f"/api/projects/{project}/permissions", headers=user_headers)
    assert effective.status_code == 200, effective.text
    assert effective.json()["REQ"] == ["comment", "view"]
    assert set(effective.json()["TC"]) == RESOURCE_ACTIONS["TC"] - {"delete", "review", "approve"}
    assert api_client.delete(f"/api/policies/{write['id']}", headers=headers).status_code == 409
    updated = api_client.patch(
        f"/api/groups/{group['id']}",
        headers=headers,
        json={"policy_ids": [read["id"]]},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["policy_ids"] == [read["id"]]
    after = api_client.get(f"/api/projects/{project}/permissions", headers=user_headers)
    assert after.status_code == 200, after.text
    assert "TC" not in after.json()
    assert (
        api_client.delete(
            f"/api/groups/{group['id']}/grants/{grant['id']}", headers=headers
        ).status_code
        == 204
    )
    assert api_client.get(f"/api/projects/{project}", headers=user_headers).status_code == 403


def test_admission_rejects_policy_selection_and_legacy_group_policy(api_client):
    headers = _admin_headers(api_client)
    project = create_project(api_client, headers, "Validation")["id"]
    policy = _policy(api_client, headers)
    group = api_client.post(
        "/api/groups", headers=headers, json={"name": unique_name("Team")}
    ).json()
    for payload in (
        {"project_id": None, "policy_ids": [policy["id"]]},
        {"project_id": project, "policy_ids": []},
        {"project_id": project, "inherit_policies": False},
    ):
        response = api_client.post(
            f"/api/groups/{group['id']}/grants", headers=headers, json=payload
        )
        assert response.status_code == 422, response.text
    response = api_client.post(
        "/api/groups",
        headers=headers,
        json={"name": unique_name("Legacy"), "policy_id": policy["id"]},
    )
    assert response.status_code == 422, response.text
    assert api_client.get(f"/api/groups/{group['id']}", headers=headers).json()["grants"] == []


def test_create_does_not_borrow_visibility_from_another_policy(api_client):
    admin = _admin_headers(api_client)
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    project = create_project(api_client, admin, "Whole create")["id"]
    read = _policy(api_client, admin, permissions={"REQ": ["view"]})
    write = _policy(
        api_client, admin, visibility="customer", permissions={"REQ": ["view", "create"]}
    )
    granted = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [read["id"], write["id"]]},
    )
    assert granted.status_code == 201, granted.text
    denied = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project, "title": "Denied internal creation", "req_origin": "Internal"},
    )
    assert denied.status_code == 403, denied.text
    allowed = api_client.post(
        "/api/requirements",
        headers=headers,
        json={
            "project_id": project,
            "title": "Allowed customer creation",
            "req_origin": "Customer",
        },
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["visibility"] == "customer"
    rows = api_client.get(f"/api/requirements?project_id={project}", headers=admin).json()["items"]
    assert [row["title"] for row in rows] == ["Allowed customer creation"]


def test_policy_rules_are_validated(api_client):
    headers = _admin_headers(api_client)
    for rules, detail in [
        ({"widget": {"read": True}}, "Unknown resources"),
        ({"REQ": {"read": True}}, "Choose at least one tag for REQ."),
        ({"link": {"read": True, "visibility": ["internal"]}}, "link takes no tags."),
        ({"REQ": {"read": True, "tags": [987654]}}, "Unknown tags"),
    ]:
        response = api_client.post(
            "/api/policies",
            headers=headers,
            json={"name": unique_name("Invalid rules"), "rules": rules},
        )
        assert response.status_code == 400, response.text
        assert detail in response.json()["detail"]


def test_approval_requires_a_policy_covering_the_requested_row(api_client):
    admin = _admin_headers(api_client)
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    project = create_project(api_client, admin, "Scoped approval")["id"]
    reader = _policy(api_client, admin, permissions={"REQ": ["view"]})
    writer = _policy(
        api_client, admin, visibility="customer", permissions={"REQ": ["view", "create", "approve"]}
    )
    assigned = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [reader["id"], writer["id"]]},
    )
    assert assigned.status_code == 201, assigned.text
    internal = api_client.post(
        "/api/requirements",
        headers=admin,
        json={
            "project_id": project,
            "title": "Internal approval",
            "req_origin": "Internal",
            "reviewer_id": api_client.get("/api/auth/me", headers=admin).json()["id"],
        },
    )
    assert internal.status_code == 201, internal.text
    customer = api_client.post(
        "/api/requirements",
        headers=headers,
        json={
            "project_id": project,
            "title": "Customer approval",
            "req_origin": "Customer",
            "reviewer_id": api_client.get("/api/auth/me", headers=admin).json()["id"],
        },
    )
    assert customer.status_code == 201, customer.text
    for created, creator, expected in [(internal, admin, 403), (customer, headers, 200)]:
        base = f"/api/artefacts/requirement/{created.json()['id']}"
        requested = api_client.post(base + "/requests", headers=creator, json={"kind": "review"})
        assert requested.status_code == 201, requested.text
        comment = api_client.post(
            base + "/comments", headers=admin, json={"body": "Reviewed revision"}
        )
        assert comment.status_code == 201, comment.text
        approval = api_client.post(base + "/requests", headers=admin, json={"kind": "approval"})
        assert approval.status_code == 201, approval.text
        decided = api_client.post(base + "/sign-off", headers=headers, json={"step": "approve"})
        assert decided.status_code == expected, decided.text
        stored = api_client.get(f"/api/requirements/{created.json()['id']}", headers=admin).json()
        assert stored["status"] == ("Approved" if expected == 200 else "Review")


def test_new_assignee_must_see_and_sign_the_proposed_artefact(api_client):
    admin = _admin_headers(api_client)
    reviewer = _create_user(api_client, admin, role="maintainer")
    project = create_project(api_client, admin, "Scoped reviewer")["id"]
    review = _policy(
        api_client, admin, visibility="customer", permissions={"REQ": ["view", "review"]}
    )
    assigned = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": reviewer["id"], "policy_ids": [review["id"]]},
    )
    assert assigned.status_code == 201, assigned.text
    denied = api_client.post(
        "/api/requirements",
        headers=admin,
        json={
            "project_id": project,
            "title": "Internal assignment",
            "req_origin": "Internal",
            "reviewer_id": reviewer["id"],
        },
    )
    assert denied.status_code == 422, denied.text
    accepted = api_client.post(
        "/api/requirements",
        headers=admin,
        json={
            "project_id": project,
            "title": "Customer assignment",
            "req_origin": "Customer",
            "reviewer_id": reviewer["id"],
        },
    )
    assert accepted.status_code == 201, accepted.text


def test_reassignment_checks_the_record_and_proposed_visibility(api_client):
    admin = _admin_headers(api_client)
    reviewer = _create_user(api_client, admin, role="maintainer")
    project = create_project(api_client, admin, "Reassignment scope")["id"]
    review = _policy(
        api_client, admin, visibility="customer", permissions={"REQ": ["view", "review"]}
    )
    assigned = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": reviewer["id"], "policy_ids": [review["id"]]},
    )
    assert assigned.status_code == 201, assigned.text
    for origin in ["Internal", "Customer"]:
        row = api_client.post(
            "/api/requirements",
            headers=admin,
            json={"project_id": project, "title": unique_name("Assign"), "req_origin": origin},
        )
        assert row.status_code == 201, row.text
        denied = api_client.patch(
            f"/api/requirements/{row.json()['id']}",
            headers=admin,
            json={"reviewer_id": reviewer["id"], "req_origin": "Internal"},
        )
        assert denied.status_code == 422, denied.text
        stored = api_client.get(f"/api/requirements/{row.json()['id']}", headers=admin).json()
        assert stored["reviewer_id"] is None
        assert stored["req_origin"] == origin


def test_defect_reviewer_permission_can_be_configured(api_client):
    admin = _admin_headers(api_client)
    reviewer = _create_user(api_client, admin, role="maintainer")
    project = create_project(api_client, admin, "Defect reviewer")["id"]
    review = _policy(api_client, admin, permissions={"DEF": ["view", "review"]})
    assigned = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": reviewer["id"], "policy_ids": [review["id"]]},
    )
    assert assigned.status_code == 201, assigned.text
    created = api_client.post(
        "/api/defects",
        headers=admin,
        json={"project_id": project, "title": "Reviewed defect", "reviewer_id": reviewer["id"]},
    )
    assert created.status_code == 201, created.text


def test_internal_customer_policy_filters_link_endpoints_and_needs_link_read(api_client):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Link scope")["id"]
    case = api_client.post(
        "/api/test-cases",
        headers=admin,
        json={"project_id": project, "title": "Case", "visibility": "customer"},
    ).json()["id"]
    links = []
    for origin in ["Customer", "Internal"]:
        requirement = api_client.post(
            "/api/requirements",
            headers=admin,
            json={"project_id": project, "title": unique_name("End"), "req_origin": origin},
        ).json()["id"]
        response = api_client.post(
            "/api/links",
            headers=admin,
            json={
                "project_id": project,
                "source_type": "TC",
                "source_id": case,
                "target_type": "REQ",
                "target_id": requirement,
                "role": "verifies",
            },
        )
        assert response.status_code == 201, response.text
        links.append(response.json()["id"])
    for link_read in [True, False]:
        user = _create_user(api_client, admin, role="maintainer")
        matrix = {"REQ": ["view"], "TC": ["view"]}
        if link_read:
            matrix["link"] = ["view"]
        policy = _policy(api_client, admin, visibility="customer", permissions=matrix)
        assigned = api_client.post(
            f"/api/projects/{project}/members",
            headers=admin,
            json={"user_id": user["id"], "policy_ids": [policy["id"]]},
        )
        assert assigned.status_code == 201, assigned.text
        response = api_client.get(
            f"/api/links?project_id={project}",
            headers=_headers_for(api_client, user["email"]),
        )
        if link_read:
            assert response.status_code == 200, response.text
            assert [row["id"] for row in response.json()] == links[:1]
        else:
            assert response.status_code == 403, response.text
