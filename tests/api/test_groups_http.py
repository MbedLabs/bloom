"""HTTP tests for the admin groups and policies API and the access it confers.

The load-bearing test is test_group_grant_confers_project_access: it proves, over
real HTTP, that a user with no direct membership gains access to exactly the
granted project through a group, and loses it when removed. The rest cover the
admin CRUD surface, the default-policy protections and admin-only enforcement.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

from tests.conftest import create_project, unique_email, unique_name

PASSWORD = "a-sufficiently-long-passphrase"


def _admin_headers(api_client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _headers_for(api_client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    login = api_client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_user(api_client, headers, role="external") -> dict:
    email = unique_email("member")
    created = api_client.post(
        "/api/users",
        headers=headers,
        json={"email": email, "full_name": "Group Member", "password": PASSWORD, "role": role},
    )
    assert created.status_code in (200, 201), created.text
    body = created.json()
    body["email"] = email
    return body


def _create_policy(api_client, headers, base_role="external") -> dict:
    created = api_client.post(
        "/api/policies",
        headers=headers,
        json={
            "name": unique_name("Policy"),
            "description": "Test policy",
            "base_role": base_role,
            "permissions": {"requirement": ["view", "comment"]},
        },
    )
    assert created.status_code == 201, created.text
    return created.json()


def _create_group(api_client, headers, policy_id=None) -> dict:
    created = api_client.post(
        "/api/groups",
        headers=headers,
        json={"name": unique_name("Group"), "description": "Test group", "policy_id": policy_id},
    )
    assert created.status_code == 201, created.text
    return created.json()


def test_default_policies_are_listed(api_client: TestClient):
    headers = _admin_headers(api_client)
    resp = api_client.get("/api/policies", headers=headers)
    assert resp.status_code == 200, resp.text
    names = {p["name"] for p in resp.json()}
    assert {"Administrator", "Customer/Stakeholder", "Developer", "Viewer"} <= names
    admin_policy = next(p for p in resp.json() if p["name"] == "Administrator")
    assert admin_policy["is_default"] is True
    assert admin_policy["base_role"] == "admin"


def test_group_crud_membership_and_grants(api_client: TestClient):
    headers = _admin_headers(api_client)
    policy = _create_policy(api_client, headers)
    user = _create_user(api_client, headers)
    project_id = create_project(api_client, headers, "Group CRUD")["id"]

    group = _create_group(api_client, headers, policy_id=policy["id"])
    assert group["members"] == [] and group["grants"] == []
    assert group["policy_id"] == policy["id"]

    # Add the user and a project grant.
    added = api_client.post(
        f"/api/groups/{group['id']}/members", headers=headers, json={"user_id": user["id"]}
    )
    assert added.status_code == 201, added.text
    assert [m["user_id"] for m in added.json()["members"]] == [user["id"]]
    assert added.json()["members"][0]["email"] == user["email"]

    # A duplicate membership is rejected.
    dup = api_client.post(
        f"/api/groups/{group['id']}/members", headers=headers, json={"user_id": user["id"]}
    )
    assert dup.status_code == 409, dup.text

    granted = api_client.post(
        f"/api/groups/{group['id']}/grants", headers=headers, json={"project_id": project_id}
    )
    assert granted.status_code == 201, granted.text
    grants = granted.json()["grants"]
    assert [g["project_id"] for g in grants] == [project_id]
    grant_id = grants[0]["id"]

    # A duplicate grant for the same project is rejected.
    dup_grant = api_client.post(
        f"/api/groups/{group['id']}/grants", headers=headers, json={"project_id": project_id}
    )
    assert dup_grant.status_code == 409, dup_grant.text

    # GET reflects the members and grants.
    fetched = api_client.get(f"/api/groups/{group['id']}", headers=headers)
    assert fetched.status_code == 200, fetched.text
    assert len(fetched.json()["members"]) == 1
    assert len(fetched.json()["grants"]) == 1

    # The group appears in the list.
    listed = api_client.get("/api/groups", headers=headers)
    assert listed.status_code == 200
    assert group["id"] in {g["id"] for g in listed.json()}

    # Remove the grant and the member.
    assert (
        api_client.delete(
            f"/api/groups/{group['id']}/grants/{grant_id}", headers=headers
        ).status_code
        == 204
    )
    assert (
        api_client.delete(
            f"/api/groups/{group['id']}/members/{user['id']}", headers=headers
        ).status_code
        == 204
    )
    emptied = api_client.get(f"/api/groups/{group['id']}", headers=headers)
    assert emptied.json()["members"] == [] and emptied.json()["grants"] == []

    # Delete the group.
    assert api_client.delete(f"/api/groups/{group['id']}", headers=headers).status_code == 204
    assert api_client.get(f"/api/groups/{group['id']}", headers=headers).status_code == 404


def test_group_grant_confers_project_access(api_client: TestClient):
    # Proves the project-role gate: a group grant lets require_project_access admit
    # a user who has no direct membership. The user is a maintainer instance role so
    # this exercises the access gate itself. Extending group grants to the external
    # document-tag visibility path is the next increment (Policy.doc_tag_scope).
    headers = _admin_headers(api_client)
    user = _create_user(api_client, headers, role="maintainer")
    user_headers = _headers_for(api_client, user["email"])
    granted_project = create_project(api_client, headers, "Granted")["id"]
    other_project = create_project(api_client, headers, "Ungranted")["id"]

    # No membership, no group: the user cannot see the project.
    assert (
        api_client.get(f"/api/projects/{granted_project}", headers=user_headers).status_code == 403
    )

    policy = _create_policy(api_client, headers, base_role="maintainer")
    group = _create_group(api_client, headers, policy_id=policy["id"])
    assert (
        api_client.post(
            f"/api/groups/{group['id']}/grants",
            headers=headers,
            json={"project_id": granted_project},
        ).status_code
        == 201
    )
    assert (
        api_client.post(
            f"/api/groups/{group['id']}/members", headers=headers, json={"user_id": user["id"]}
        ).status_code
        == 201
    )

    # The grant now lets the user reach exactly the granted project, not the other.
    assert (
        api_client.get(f"/api/projects/{granted_project}", headers=user_headers).status_code == 200
    )
    assert api_client.get(f"/api/projects/{other_project}", headers=user_headers).status_code == 403

    # Removing the user from the group revokes the access again.
    assert (
        api_client.delete(
            f"/api/groups/{group['id']}/members/{user['id']}", headers=headers
        ).status_code
        == 204
    )
    assert (
        api_client.get(f"/api/projects/{granted_project}", headers=user_headers).status_code == 403
    )


def test_default_policies_are_protected(api_client: TestClient):
    headers = _admin_headers(api_client)
    policies = api_client.get("/api/policies", headers=headers).json()
    default = next(p for p in policies if p["is_default"])
    # A default whose base_role is not already admin, so the change below is real.
    non_admin_default = next(p for p in policies if p["is_default"] and p["base_role"] != "admin")
    assert non_admin_default["base_role"] != "admin"

    # A default cannot be deleted, and its base role cannot change.
    assert api_client.delete(f"/api/policies/{default['id']}", headers=headers).status_code == 400
    changed = api_client.patch(
        f"/api/policies/{non_admin_default['id']}", headers=headers, json={"base_role": "admin"}
    )
    assert changed.status_code == 400, changed.text

    # A custom policy can be created, retuned and deleted.
    custom = _create_policy(api_client, headers)
    assert custom["is_default"] is False
    retuned = api_client.patch(
        f"/api/policies/{custom['id']}", headers=headers, json={"base_role": "maintainer"}
    )
    assert retuned.status_code == 200 and retuned.json()["base_role"] == "maintainer"
    assert api_client.delete(f"/api/policies/{custom['id']}", headers=headers).status_code == 204


def test_policy_in_use_cannot_be_deleted(api_client: TestClient):
    headers = _admin_headers(api_client)
    policy = _create_policy(api_client, headers)
    group = _create_group(api_client, headers, policy_id=policy["id"])

    assert api_client.delete(f"/api/policies/{policy['id']}", headers=headers).status_code == 409

    # Once no group references it, the policy can be deleted.
    assert api_client.delete(f"/api/groups/{group['id']}", headers=headers).status_code == 204
    assert api_client.delete(f"/api/policies/{policy['id']}", headers=headers).status_code == 204


def test_groups_and_policies_are_admin_only(api_client: TestClient):
    headers = _admin_headers(api_client)
    user = _create_user(api_client, headers, role="external")
    user_headers = _headers_for(api_client, user["email"])

    assert api_client.get("/api/groups", headers=user_headers).status_code == 403
    assert api_client.get("/api/policies", headers=user_headers).status_code == 403
    assert (
        api_client.post(
            "/api/groups", headers=user_headers, json={"name": unique_name("Nope")}
        ).status_code
        == 403
    )
