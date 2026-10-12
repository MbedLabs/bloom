"""Project bundle assignments and application grants keep their scopes separate."""

from tests.api.test_groups_http import _admin_headers, _create_user, _headers_for
from tests.api.test_project_policy_grants_http import _policy
from tests.conftest import create_project, unique_name


def _group(client, admin, policies):
    """Create a bundle containing the supplied policies."""
    response = client.post(
        "/api/groups",
        headers=admin,
        json={"name": unique_name("Bundle"), "policy_ids": [p["id"] for p in policies]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_same_user_has_different_bundles_on_two_projects(api_client):
    admin = _admin_headers(api_client)
    projects = [create_project(api_client, admin, name)["id"] for name in ["Author", "Reader"]]
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    write = _policy(api_client, admin, permissions={"REQ": ["view", "create", "edit"]})
    read = _policy(api_client, admin, visibility="customer")
    bundles = [_group(api_client, admin, [write]), _group(api_client, admin, [read])]
    entries = []
    for project, bundle in zip(projects, bundles):
        response = api_client.post(
            f"/api/projects/{project}/members",
            headers=admin,
            json={"user_id": user["id"], "policy_group_id": bundle["id"]},
        )
        assert response.status_code == 201, response.text
        entries.append(response.json())
    first = api_client.get(f"/api/projects/{projects[0]}/permissions", headers=headers).json()
    second = api_client.get(f"/api/projects/{projects[1]}/permissions", headers=headers).json()
    assert "create" in first["REQ"] and "create" not in second["REQ"]
    for bundle in bundles:
        assert api_client.get(f"/api/groups/{bundle['id']}", headers=admin).json()["members"] == []
    for project, origin in zip(projects, ["internal", "customer"]):
        result = api_client.post(
            "/api/requirements",
            headers=headers,
            json={"project_id": project, "title": unique_name("Requirement"), "visibility": origin},
        )
        assert result.status_code == (201 if project == projects[0] else 403), result.text
    changed = api_client.patch(
        f"/api/groups/{bundles[0]['id']}", headers=admin, json={"policy_ids": [read["id"]]}
    )
    assert changed.status_code == 200, changed.text
    assert (
        "create"
        not in api_client.get(f"/api/projects/{projects[0]}/permissions", headers=headers).json()[
            "REQ"
        ]
    )


def test_access_manager_assigns_atomically_without_project_or_user_admin_access(api_client):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Assignment")["id"]
    manager = _create_user(api_client, admin, role="maintainer")
    people = [_create_user(api_client, admin, role="maintainer") for _ in range(2)]
    headers = _headers_for(api_client, manager["email"])
    assert api_client.get("/api/tags", headers=headers).status_code == 403
    policies = api_client.get("/api/policies", headers=admin).json()
    access = next(p for p in policies if p["name"] == "Access Management")
    read = next(p for p in policies if p["name"] == "Read Customer")
    granted = api_client.put(
        f"/api/users/{manager['id']}/application-policies",
        headers=admin,
        json={"policy_ids": [access["id"]]},
    )
    assert granted.status_code == 200, granted.text
    assert api_client.get("/api/tags", headers=admin).status_code == 200
    assert api_client.get("/api/tags", headers=headers).status_code == 200
    assert api_client.get("/api/users", headers=headers).status_code == 403
    assert api_client.get(f"/api/projects/{project}", headers=headers).status_code == 403
    assert api_client.get("/api/groups/assignment-options", headers=headers).status_code == 200
    bundle = _group(api_client, admin, [read])
    before = api_client.get(f"/api/projects/{project}/members", headers=admin).json()
    invalid = api_client.post(
        f"/api/groups/{bundle['id']}/assignments",
        headers=headers,
        json={"project_id": project, "user_ids": [people[0]["id"], 2147483647]},
    )
    assert invalid.status_code == 404, invalid.text
    assert api_client.get(f"/api/projects/{project}/members", headers=admin).json() == before
    assigned = api_client.post(
        f"/api/groups/{bundle['id']}/assignments",
        headers=headers,
        json={"project_id": project, "user_ids": [p["id"] for p in people]},
    )
    assert assigned.status_code == 200, assigned.text
    assert {m["policy_group_id"] for m in assigned.json()} == {bundle["id"]}
    assert (
        len(api_client.get(f"/api/projects/{project}/members", headers=admin).json())
        == len(before) + 2
    )
    assert api_client.get(f"/api/projects/{project}", headers=headers).status_code == 403
    assert api_client.get("/api/users", headers=headers).status_code == 403
    assert api_client.get("/api/auth/me", headers=headers).json()["application_permissions"][
        "access"
    ]


def test_project_administrators_bundle_does_not_grant_app_administration(api_client):
    admin = _admin_headers(api_client)
    first = create_project(api_client, admin, "Project administrator")["id"]
    second = create_project(api_client, admin, "Another project")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    bundle = next(
        g
        for g in api_client.get("/api/groups", headers=admin).json()
        if g["name"] == "Administrators"
    )
    assigned = api_client.post(
        f"/api/projects/{first}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_group_id": bundle["id"]},
    )
    assert assigned.status_code == 201, assigned.text
    assert (
        api_client.patch(
            f"/api/projects/{first}", headers=headers, json={"description": "Updated"}
        ).status_code
        == 200
    )
    assert api_client.get(f"/api/projects/{second}", headers=headers).status_code == 403
    assert api_client.get("/api/groups", headers=headers).status_code == 403
    assert api_client.get("/api/users", headers=headers).status_code == 403
    assert api_client.delete(f"/api/projects/{first}", headers=headers).status_code == 403


def test_app_assignment_rejects_content_policy_and_preserves_base_role(api_client):
    admin = _admin_headers(api_client)
    user = _create_user(api_client, admin, role="external")
    policy = _policy(api_client, admin)
    rejected = api_client.put(
        f"/api/users/{user['id']}/application-policies",
        headers=admin,
        json={"policy_ids": [policy["id"]]},
    )
    assert rejected.status_code == 400, rejected.text
    assert api_client.get(f"/api/users/{user['id']}", headers=admin).json()["role"] == "external"


def test_viewer_app_grant_keeps_base_role_caps_and_no_project_admission(api_client):
    admin = _admin_headers(api_client)
    user = _create_user(api_client, admin, role="external")
    headers = _headers_for(api_client, user["email"])
    access = next(
        p
        for p in api_client.get("/api/policies", headers=admin).json()
        if p["name"] == "Access Management"
    )
    saved = api_client.put(
        f"/api/users/{user['id']}/application-policies",
        headers=admin,
        json={"policy_ids": [access["id"]]},
    )
    assert saved.status_code == 200, saved.text
    permissions = api_client.get("/api/users/me/application-permissions", headers=headers).json()
    assert "edit" in permissions["access"] and "delete" not in permissions["access"]
    assert api_client.get("/api/groups/assignment-options", headers=headers).status_code == 200
    assert api_client.get("/api/projects", headers=headers).json() == []
    assert api_client.get(f"/api/users/{user['id']}", headers=admin).json()["role"] == "external"


def test_project_group_assignment_rejects_mixed_modes_and_missing_group(api_client):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Validation")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    group = _group(api_client, admin, [_policy(api_client, admin)])
    mixed = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_group_id": group["id"], "owner": True},
    )
    assert mixed.status_code == 422, mixed.text
    missing = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_group_id": 2147483647},
    )
    assert missing.status_code == 404, missing.text
    valid = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_group_id": group["id"]},
    )
    assert valid.status_code == 201, valid.text
    rejected = api_client.patch(
        f"/api/projects/{project}/members/{valid.json()['id']}",
        headers=admin,
        json={"policy_group_id": group["id"], "inherit_policies": True},
    )
    assert rejected.status_code == 422, rejected.text
    assert (
        api_client.get(
            f"/api/projects/{project}/members/{valid.json()['id']}", headers=admin
        ).json()["policy_group_id"]
        == group["id"]
    )


def test_assigned_application_policy_cannot_change_scope(api_client):
    admin = _admin_headers(api_client)
    user = _create_user(api_client, admin, role="maintainer")
    created = api_client.post(
        "/api/policies",
        headers=admin,
        json={
            "name": unique_name("App scope guard"),
            "scope": "app",
            "rules": {"access": {"read": True, "write": True, "delete": True}},
        },
    )
    assert created.status_code == 201, created.text
    editable = created.json()
    assignment = {"policy_ids": [editable["id"]]}
    assert (
        api_client.put(
            f"/api/users/{user['id']}/application-policies", headers=admin, json=assignment
        ).status_code
        == 200
    )
    changed = api_client.patch(
        f"/api/policies/{editable['id']}",
        headers=admin,
        json={"scope": "project", "rules": {"project": {"read": True}}},
    )
    assert changed.status_code == 409, changed.text
    assert api_client.get(f"/api/policies/{editable['id']}", headers=admin).json()["scope"] == "app"
    assert (
        api_client.put(
            f"/api/users/{user['id']}/application-policies", headers=admin, json=assignment
        ).status_code
        == 200
    )


def test_administrators_bundle_can_be_assigned_to_different_people_on_two_projects(api_client):
    admin = _admin_headers(api_client)
    projects = [create_project(api_client, admin, unique_name("Roster"))["id"] for _ in range(2)]
    people = [_create_user(api_client, admin, role="maintainer") for _ in range(2)]
    account_admin = _create_user(api_client, admin, role="admin")
    bundle = next(
        g
        for g in api_client.get("/api/groups", headers=admin).json()
        if g["name"] == "Administrators"
    )
    choices = api_client.get("/api/groups/assignment-options", headers=admin).json()
    assert account_admin["id"] in {person["id"] for person in choices["users"]}
    for project, person in zip(projects, people):
        response = api_client.post(
            f"/api/groups/{bundle['id']}/assignments",
            headers=admin,
            json={"project_id": project, "user_ids": [person["id"], account_admin["id"]]},
        )
        assert response.status_code == 200, response.text
        assert {entry["user_id"] for entry in response.json()} == {
            person["id"],
            account_admin["id"],
        }
        headers = _headers_for(api_client, person["email"])
        assert (
            api_client.patch(
                f"/api/projects/{project}", headers=headers, json={"description": "Updated"}
            ).status_code
            == 200
        )
        other = next(value for value in projects if value != project)
        assert api_client.get(f"/api/projects/{other}", headers=headers).status_code == 403
        assert api_client.get("/api/users", headers=headers).status_code == 403
    assert api_client.get(f"/api/groups/{bundle['id']}", headers=admin).json()["members"] == []
    assert (
        api_client.get(f"/api/users/{account_admin['id']}", headers=admin).json()["role"] == "admin"
    )
