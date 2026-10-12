"""HTTP tests for the admin groups and policies API and the access it confers.

The load-bearing test is test_group_grant_confers_project_access: it proves, over
real HTTP, that a user with no direct membership gains access to exactly the
granted project through a group, and loses it when removed. The rest cover the
admin CRUD surface, the default-policy protections and admin-only enforcement.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

from app.core.permissions import DOC_TYPE_RESOURCES
from tests.api.test_document_workflow_http import workflow_http
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


def _create_policy(api_client, headers, base_role="external", doc_tag_scope=None) -> dict:
    shown = ["customer"] if base_role == "external" else ["internal", "customer"]
    body = {
        "name": unique_name("Policy"),
        "description": "Test policy",
        "rules": {
            doc_type: {"read": True, "visibility": shown} for doc_type in doc_tag_scope or ["REQ"]
        },
    }
    created = api_client.post("/api/policies", headers=headers, json=body)
    assert created.status_code == 201, created.text
    return created.json()


def _create_group(api_client, headers, policy_id=None) -> dict:
    created = api_client.post(
        "/api/groups",
        headers=headers,
        json={
            "name": unique_name("Group"),
            "description": "Test group",
            "policy_ids": [policy_id] if policy_id is not None else [],
        },
    )
    assert created.status_code == 201, created.text
    return created.json()


def test_default_policies_are_listed(api_client: TestClient):
    headers = _admin_headers(api_client)
    resp = api_client.get("/api/policies", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()
    assert all("base_role" not in policy for policy in resp.json())
    defaults = [policy for policy in resp.json() if policy["is_default"]]
    from app.core.policy_seed import DEFAULT_POLICIES

    assert len(defaults) == 23
    assert {policy["name"] for policy in defaults} == {spec["name"] for spec in DEFAULT_POLICIES}
    for policy in defaults:
        origin = {"Read Customer": "customer", "Review Customer": "customer"}.get(policy["name"])
        for doc_type in set(policy["rules"]) & set(DOC_TYPE_RESOURCES):
            assert policy["rules"][doc_type]["all_origins"] is (origin is None)
            assert policy["rules"][doc_type]["visibility"] == ([origin] if origin else [])
            assert policy["rules"][doc_type]["tags"] == []


async def test_review_only_policy_roundtrips_and_requires_origin(workflow_http):
    _, client, _, _ = workflow_http
    rule = {
        "read": False,
        "write": False,
        "review": True,
        "approve": False,
        "delete": False,
        "visibility": ["customer"],
    }
    created = await client.post(
        "/api/policies",
        json={"name": unique_name("Review only"), "scope": "document", "rules": {"REQ": rule}},
    )
    assert created.status_code == 201, created.text
    policy = created.json()
    shown = await client.get(f"/api/policies/{policy['id']}")
    assert shown.status_code == 200, shown.text
    assert shown.json()["rules"]["REQ"] == {
        **rule,
        "all_origins": False,
        "tags": [],
        "actions": ["review"],
    }
    updated = await client.patch(
        f"/api/policies/{policy['id']}",
        json={"rules": {"REQ": {**rule, "visibility": ["internal"]}}},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["rules"]["REQ"] == {
        **rule,
        "visibility": ["internal"],
        "all_origins": False,
        "tags": [],
        "actions": ["review"],
    }
    unscoped = await client.post(
        "/api/policies",
        json={"name": unique_name("Unscoped review"), "rules": {"REQ": {"review": True}}},
    )
    assert unscoped.status_code == 400, unscoped.text
    assert "Choose at least one tag for REQ" in unscoped.json()["detail"]


async def test_review_defaults_read_through_the_actual_policy_api(workflow_http):
    from app.core.policy_seed import DEFAULT_POLICIES
    from app.models.groups import Policy

    db, client, _, _ = workflow_http
    db.add_all([Policy(**spec, is_default=True) for spec in DEFAULT_POLICIES])
    await db.flush()
    response = await client.get("/api/policies")
    assert response.status_code == 200, response.text
    defaults = {policy["name"]: policy for policy in response.json() if policy["is_default"]}
    assert len(defaults) == 23
    for name, origin in [("Review Internal", None), ("Review Customer", "customer")]:
        rules = defaults[name]["rules"]
        assert set(rules) == set(DOC_TYPE_RESOURCES)
        for rule in rules.values():
            assert rule["review"] is True
            assert rule["read"] is rule["write"] is rule["approve"] is rule["delete"] is False
            assert rule["all_origins"] is (origin is None)
            assert rule["visibility"] == ([origin] if origin else [])
            assert rule["actions"] == ["review"]


def test_group_crud_membership_and_grants(api_client: TestClient):
    headers = _admin_headers(api_client)
    policy = _create_policy(api_client, headers)
    user = _create_user(api_client, headers)
    project_id = create_project(api_client, headers, "Group CRUD")["id"]

    group = _create_group(api_client, headers, policy_id=policy["id"])
    assert group["members"] == [] and group["grants"] == []
    assert "policy_id" not in group

    added = api_client.post(
        f"/api/groups/{group['id']}/members", headers=headers, json={"user_id": user["id"]}
    )
    assert added.status_code == 201, added.text
    assert [m["user_id"] for m in added.json()["members"]] == [user["id"]]
    assert added.json()["members"][0]["email"] == user["email"]

    dup = api_client.post(
        f"/api/groups/{group['id']}/members", headers=headers, json={"user_id": user["id"]}
    )
    assert dup.status_code == 409, dup.text

    granted = api_client.post(
        f"/api/groups/{group['id']}/grants",
        headers=headers,
        json={"project_id": project_id},
    )
    assert granted.status_code == 201, granted.text
    grants = granted.json()["grants"]
    assert [g["project_id"] for g in grants] == [project_id]
    grant_id = grants[0]["id"]

    dup_grant = api_client.post(
        f"/api/groups/{group['id']}/grants",
        headers=headers,
        json={"project_id": project_id},
    )
    assert dup_grant.status_code == 409, dup_grant.text

    fetched = api_client.get(f"/api/groups/{group['id']}", headers=headers)
    assert fetched.status_code == 200, fetched.text
    assert len(fetched.json()["members"]) == 1
    assert len(fetched.json()["grants"]) == 1

    listed = api_client.get("/api/groups", headers=headers)
    assert listed.status_code == 200
    assert group["id"] in {g["id"] for g in listed.json()}

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

    assert api_client.delete(f"/api/groups/{group['id']}", headers=headers).status_code == 204
    assert api_client.get(f"/api/groups/{group['id']}", headers=headers).status_code == 404


def test_group_grant_confers_project_access(api_client: TestClient):
    headers = _admin_headers(api_client)
    user = _create_user(api_client, headers, role="maintainer")
    user_headers = _headers_for(api_client, user["email"])
    granted_project = create_project(api_client, headers, "Granted")["id"]
    other_project = create_project(api_client, headers, "Ungranted")["id"]

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

    assert (
        api_client.get(f"/api/projects/{granted_project}", headers=user_headers).status_code == 200
    )
    assert api_client.get(f"/api/projects/{other_project}", headers=user_headers).status_code == 403

    assert (
        api_client.delete(
            f"/api/groups/{group['id']}/members/{user['id']}", headers=headers
        ).status_code
        == 204
    )
    assert (
        api_client.get(f"/api/projects/{granted_project}", headers=user_headers).status_code == 403
    )


def test_group_grant_admits_external_user_scoped_by_policy(api_client: TestClient):
    headers = _admin_headers(api_client)
    user = _create_user(api_client, headers, role="external")
    user_headers = _headers_for(api_client, user["email"])
    project_id = create_project(api_client, headers, "ExtGrant")["id"]

    assert api_client.get(f"/api/projects/{project_id}", headers=user_headers).status_code == 403

    policy = _create_policy(api_client, headers, base_role="external", doc_tag_scope=["REQ", "TC"])
    group = _create_group(api_client, headers, policy_id=policy["id"])
    api_client.post(
        f"/api/groups/{group['id']}/grants",
        headers=headers,
        json={"project_id": project_id},
    )
    api_client.post(
        f"/api/groups/{group['id']}/members", headers=headers, json={"user_id": user["id"]}
    )

    assert api_client.get(f"/api/projects/{project_id}", headers=user_headers).status_code == 200


def test_policy_rejects_unknown_doc_types(api_client: TestClient):
    headers = _admin_headers(api_client)
    bad = api_client.post(
        "/api/policies",
        headers=headers,
        json={
            "name": unique_name("BadPolicy"),
            "rules": {"NOPE": {"read": True, "visibility": ["customer"]}},
        },
    )
    assert bad.status_code == 400, bad.text
    assert "NOPE" in bad.text


def test_default_policies_are_protected(api_client: TestClient):
    headers = _admin_headers(api_client)
    policies = api_client.get("/api/policies", headers=headers).json()
    default = next(p for p in policies if p["is_default"])
    non_admin_default = next(p for p in policies if p["is_default"])

    assert api_client.delete(f"/api/policies/{default['id']}", headers=headers).status_code == 400
    for body in ({"name": "x"}, {"description": "x"}, {"rules": {}}):
        changed = api_client.patch(
            f"/api/policies/{non_admin_default['id']}", headers=headers, json=body
        )
        assert changed.status_code == 403, changed.text
        assert (
            changed.json()["detail"]
            == "Default policies are read-only; duplicate one to change it."
        )

    copy = api_client.post(f"/api/policies/{non_admin_default['id']}/duplicate", headers=headers)
    assert copy.status_code == 201, copy.text
    assert copy.json()["name"] == f"{non_admin_default['name']} (copy)"
    assert copy.json()["is_default"] is False
    assert copy.json()["rules"] == non_admin_default["rules"]
    again = api_client.post(f"/api/policies/{non_admin_default['id']}/duplicate", headers=headers)
    assert again.json()["name"] == f"{non_admin_default['name']} (copy 2)"
    edited = api_client.patch(
        f"/api/policies/{copy.json()['id']}", headers=headers, json={"description": "mine"}
    )
    assert edited.status_code == 200, edited.text
    for made in (copy.json(), again.json()):
        assert api_client.delete(f"/api/policies/{made['id']}", headers=headers).status_code == 204

    custom = _create_policy(api_client, headers)
    assert custom["is_default"] is False
    retuned = api_client.patch(
        f"/api/policies/{custom['id']}",
        headers=headers,
        json={"rules": {"REQ": {"read": True, "visibility": ["internal"]}}},
    )
    assert retuned.status_code == 200, retuned.text
    assert retuned.json()["rules"]["REQ"]["visibility"] == ["internal"]
    assert api_client.delete(f"/api/policies/{custom['id']}", headers=headers).status_code == 204


def test_policy_in_use_cannot_be_deleted(api_client: TestClient):
    headers = _admin_headers(api_client)
    policy = _create_policy(api_client, headers)
    group = _create_group(api_client, headers, policy_id=policy["id"])

    project = create_project(api_client, headers, "Policy in use")["id"]
    grant = api_client.post(
        f"/api/groups/{group['id']}/grants",
        headers=headers,
        json={"project_id": project},
    )
    assert grant.status_code == 201, grant.text

    assert api_client.delete(f"/api/policies/{policy['id']}", headers=headers).status_code == 409

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
