"""Group-owned rules apply to admitted users without combining action and origin scopes."""

from tests.api.test_groups_http import _admin_headers, _create_user, _headers_for
from tests.conftest import create_project, unique_name


def _rule_policy(client, admin, resource, **rule):
    """Create a resource policy through the public policy contract."""
    response = client.post(
        "/api/policies",
        headers=admin,
        json={
            "name": unique_name("Resource policy"),
            "scope": "document",
            "rules": {resource: {"read": True, "all_origins": True, **rule}},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_group_definition_owns_multiple_policies(api_client):
    admin = _admin_headers(api_client)
    requirements = _rule_policy(api_client, admin, "REQ", write=True)
    test_cases = _rule_policy(api_client, admin, "TC", approve=True)
    response = api_client.post(
        "/api/groups",
        headers=admin,
        json={
            "name": unique_name("Document control"),
            "policy_ids": [requirements["id"], test_cases["id"]],
        },
    )
    assert response.status_code == 201, response.text
    group = response.json()
    assert set(group["policy_ids"]) == {requirements["id"], test_cases["id"]}
    assert group["members"] == []
    assert group["grants"] == []
    updated = api_client.patch(
        f"/api/groups/{group['id']}",
        headers=admin,
        json={"policy_ids": [requirements["id"]]},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["policy_ids"] == [requirements["id"]]
    assert (
        api_client.delete(f"/api/policies/{requirements['id']}", headers=admin).status_code == 409
    )


def test_write_does_not_grant_signoff_and_approve_does_not_grant_write(api_client):
    admin = _admin_headers(api_client)
    write = _rule_policy(api_client, admin, "REQ", write=True)
    approve = _rule_policy(api_client, admin, "REQ", approve=True)
    assert {"create", "edit"} <= set(write["rules"]["REQ"]["actions"])
    assert not {"approve", "review", "delete"} & set(write["rules"]["REQ"]["actions"])
    assert {"review", "approve"} <= set(approve["rules"]["REQ"]["actions"])
    assert not {"create", "edit", "delete"} & set(approve["rules"]["REQ"]["actions"])
    project = create_project(api_client, admin, "Independent approval")["id"]
    author = _create_user(api_client, admin, role="maintainer")
    signer = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, author["email"])
    signer_headers = _headers_for(api_client, signer["email"])
    for user, policy in ((author, write), (signer, approve)):
        membership = api_client.post(
            f"/api/projects/{project}/members",
            headers=admin,
            json={"user_id": user["id"], "policy_ids": [policy["id"]]},
        )
        assert membership.status_code == 201, membership.text
    created = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project, "title": "Controlled requirement", "status": "Draft"},
    )
    assert created.status_code == 201, created.text
    requirement = created.json()["id"]
    path = f"/api/artefacts/requirement/{requirement}"
    assigned = api_client.put(
        path + "/workflow/assignees",
        headers=admin,
        json={"reviewer_id": signer["id"], "approver_id": signer["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    requested = api_client.post(path + "/requests", headers=headers, json={"kind": "review"})
    assert requested.status_code == 201, requested.text
    refused = api_client.post(path + "/sign-off", headers=headers, json={"step": "review"})
    assert refused.status_code == 403, refused.text
    denied_edit = api_client.patch(
        f"/api/requirements/{requirement}", headers=signer_headers, json={"title": "No Write"}
    )
    assert denied_edit.status_code == 403, denied_edit.text
    assert denied_edit.json()["detail"] == "Missing permission: edit on REQ."
    comment = api_client.post(
        path + "/comments", headers=signer_headers, json={"body": "Reviewed requested content"}
    )
    assert comment.status_code == 201, comment.text
    reviewed = api_client.post(path + "/sign-off", headers=signer_headers, json={"step": "review"})
    assert reviewed.status_code == 200, reviewed.text
    denied_approval = api_client.post(path + "/sign-off", headers=headers, json={"step": "approve"})
    assert denied_approval.status_code == 403, denied_approval.text
    approved = api_client.post(path + "/sign-off", headers=signer_headers, json={"step": "approve"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["reviewed_by_id"] == signer["id"]
    assert approved.json()["approved_by_id"] == signer["id"]
    stored = api_client.get(f"/api/requirements/{requirement}", headers=admin)
    assert stored.status_code == 200, stored.text
    assert stored.json()["status"] == "Approved"


def test_unsupported_approval_is_rejected(api_client):
    admin = _admin_headers(api_client)
    response = api_client.post(
        "/api/policies",
        headers=admin,
        json={
            "name": unique_name("Invalid approval"),
            "scope": "document",
            "rules": {"STD": {"read": True, "approve": True, "all_origins": True}},
        },
    )
    assert response.status_code == 400, response.text


def test_project_assignment_blocks_changing_a_policy_to_app_scope(api_client):
    admin = _admin_headers(api_client)
    policy = _rule_policy(api_client, admin, "REQ")
    project = create_project(api_client, admin, "Policy assignment scope")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    assigned = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [policy["id"]]},
    )
    assert assigned.status_code == 201, assigned.text
    changed = api_client.patch(
        f"/api/policies/{policy['id']}", headers=admin, json={"scope": "app"}
    )
    assert changed.status_code == 409, changed.text
    unchanged = api_client.get(f"/api/policies/{policy['id']}", headers=admin)
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["scope"] == "document"


def test_all_origins_covers_origins_added_after_assignment(api_client):
    admin = _admin_headers(api_client)
    policy = _rule_policy(api_client, admin, "REQ", write=True)
    project = create_project(api_client, admin, "Future origins")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    assigned = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [policy["id"]]},
    )
    assert assigned.status_code == 201, assigned.text
    origin = api_client.post("/api/tags", headers=admin, json={"name": unique_name("Partner")})
    assert origin.status_code == 201, origin.text
    created = api_client.post(
        "/api/requirements",
        headers=admin,
        json={
            "project_id": project,
            "title": "A newly classified requirement",
            "tag_ids": [origin.json()["id"]],
        },
    )
    assert created.status_code == 201, created.text
    requirement = created.json()["id"]
    detail = api_client.get(f"/api/requirements/{requirement}", headers=headers)
    assert detail.status_code == 200, detail.text
    listed = api_client.get(f"/api/requirements?project_id={project}", headers=headers)
    assert listed.status_code == 200, listed.text
    assert requirement in {row["id"] for row in listed.json()["items"]}
    edited = api_client.patch(
        f"/api/requirements/{requirement}",
        headers=headers,
        json={"title": "Updated classification"},
    )
    assert edited.status_code == 200, edited.text


def test_project_override_replaces_inherited_group_permissions(api_client):
    admin = _admin_headers(api_client)
    write = _rule_policy(api_client, admin, "REQ", write=True)
    read = _rule_policy(api_client, admin, "REQ")
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    group = api_client.post(
        "/api/groups",
        headers=admin,
        json={"name": unique_name("Requirements control"), "policy_ids": [write["id"]]},
    )
    assert group.status_code == 201, group.text
    joined = api_client.post(
        f"/api/groups/{group.json()['id']}/members",
        headers=admin,
        json={"user_id": user["id"]},
    )
    assert joined.status_code == 201, joined.text
    projects = [
        create_project(api_client, admin, label)["id"] for label in ("Inherited", "Explicit")
    ]
    first = api_client.post(
        f"/api/projects/{projects[0]}/members",
        headers=admin,
        json={"user_id": user["id"], "inherit_policies": True},
    )
    second = api_client.post(
        f"/api/projects/{projects[1]}/members",
        headers=admin,
        json={"user_id": user["id"], "inherit_policies": False, "policy_ids": [read["id"]]},
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    admitted_group = api_client.post(
        f"/api/groups/{group.json()['id']}/grants",
        headers=admin,
        json={"project_id": projects[1]},
    )
    assert admitted_group.status_code == 201, admitted_group.text
    allowed = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": projects[0], "title": "Inherited Write"},
    )
    refused = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": projects[1], "title": "Explicit Read"},
    )
    assert allowed.status_code == 201, allowed.text
    assert refused.status_code == 403, refused.text
    assert (
        "create"
        not in api_client.get(f"/api/projects/{projects[1]}/permissions", headers=headers).json()[
            "REQ"
        ]
    )
    other = create_project(api_client, admin, "Not admitted")["id"]
    assert api_client.get(f"/api/projects/{other}", headers=headers).status_code == 403


def test_external_cap_retains_selected_review_and_refuses_approve_and_delete(api_client):
    admin = _admin_headers(api_client)
    policy = _rule_policy(api_client, admin, "REQ", write=True, approve=True, delete=True)
    project = create_project(api_client, admin, "External ceiling")["id"]
    user = _create_user(api_client, admin, role="external")
    headers = _headers_for(api_client, user["email"])
    admitted = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [policy["id"]]},
    )
    assert admitted.status_code == 201, admitted.text
    permissions = api_client.get(f"/api/projects/{project}/permissions", headers=headers)
    assert permissions.status_code == 200, permissions.text
    assert "review" in permissions.json()["REQ"]
    assert not {"approve", "delete"} & set(permissions.json()["REQ"])
    created = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": "Customer review", "req_origin": "Customer"},
    )
    assert created.status_code == 201, created.text
    requirement = created.json()["id"]
    path = f"/api/artefacts/requirement/{requirement}"
    unassigned = api_client.post(path + "/comments", headers=headers, json={"body": "Unassigned"})
    assert unassigned.status_code == 403, unassigned.text
    assigned = api_client.put(
        path + "/workflow/assignees", headers=admin, json={"reviewer_id": user["id"]}
    )
    assert assigned.status_code == 200, assigned.text
    comment = api_client.post(path + "/comments", headers=headers, json={"body": "Customer review"})
    assert comment.status_code == 201, comment.text
    denied_assignment = api_client.put(
        path + "/workflow/assignees", headers=admin, json={"approver_id": user["id"]}
    )
    assert denied_assignment.status_code == 422, denied_assignment.text
    deleted = api_client.delete(f"/api/requirements/{requirement}", headers=headers)
    assert deleted.status_code == 403, deleted.text
    assert deleted.json()["detail"] == "Missing permission: delete on REQ."
    hidden = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": "Internal review", "req_origin": "Internal"},
    )
    assert hidden.status_code == 201, hidden.text
    refused = api_client.post(
        f"/api/artefacts/requirement/{hidden.json()['id']}/comments",
        headers=headers,
        json={"body": "Hidden"},
    )
    assert refused.status_code == 404, refused.text


def test_all_origins_does_not_lend_scope_to_a_narrow_write_rule(api_client):
    admin = _admin_headers(api_client)
    read = _rule_policy(api_client, admin, "REQ")
    write = _rule_policy(
        api_client, admin, "REQ", write=True, all_origins=False, visibility=["customer"]
    )
    project = create_project(api_client, admin, "Origin scopes")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    admitted = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [read["id"], write["id"]]},
    )
    assert admitted.status_code == 201, admitted.text
    created = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": "Internal requirement", "visibility": "internal"},
    )
    assert created.status_code == 201, created.text
    row = created.json()["id"]
    assert api_client.get(f"/api/requirements/{row}", headers=headers).status_code == 200
    denied = api_client.patch(
        f"/api/requirements/{row}", headers=headers, json={"title": "Scope escalation"}
    )
    assert denied.status_code == 403, denied.text


def test_project_override_rejects_application_policy(api_client):
    admin = _admin_headers(api_client)
    policy = api_client.post(
        "/api/policies",
        headers=admin,
        json={
            "name": unique_name("User management"),
            "scope": "app",
            "rules": {"users": {"read": True, "write": True}},
        },
    )
    assert policy.status_code == 201, policy.text
    project = create_project(api_client, admin, "Application boundary")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    denied = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [policy.json()["id"]]},
    )
    assert denied.status_code == 400, denied.text
