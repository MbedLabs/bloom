"""Direct user entries use selected policies or a project-specific Owner grant."""

from tests.api.test_groups_http import _admin_headers, _create_user, _headers_for
from tests.api.test_project_policy_grants_http import _policy
from tests.conftest import create_project


def test_direct_policy_entry_controls_access_and_report(api_client):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Direct policies")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    read = _policy(api_client, admin, types=["REQ"])
    write = _policy(api_client, admin, permissions={"TC": ["view", "create", "edit"]}, types=["TC"])
    created = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [read["id"], write["id"]]},
    )
    assert created.status_code == 201, created.text
    entry = created.json()
    assert entry["owner"] is False
    assert set(entry["policy_ids"]) == {read["id"], write["id"]}
    assert "role" not in entry
    assert "doc_types" not in entry
    assert api_client.get(f"/api/projects/{project}", headers=headers).status_code == 200
    report = api_client.get(f"/api/projects/{project}/access", headers=admin).json()
    person = next(item for item in report if item["user_id"] == user["id"])
    assert person["origins"] == [
        {
            "kind": "direct",
            "owner": False,
            "inherit_policies": False,
            "group": None,
            "policies": [read["name"], write["name"]],
        }
    ]
    updated = api_client.patch(
        f"/api/projects/{project}/members/{entry['id']}",
        headers=admin,
        json={"policy_ids": [read["id"]]},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["policy_ids"] == [read["id"]]


def test_owner_grant_is_project_specific_and_keeps_administration_reserved(api_client):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Owned")["id"]
    other = create_project(api_client, admin, "Other")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    created = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "owner": True, "policy_ids": []},
    )
    assert created.status_code == 201, created.text
    assert created.json()["owner"] is True
    capabilities = api_client.get(f"/api/projects/{project}/capabilities", headers=headers)
    assert capabilities.status_code == 200, capabilities.text
    assert capabilities.json() == {
        "can_edit": True,
        "can_delete": False,
        "can_manage_access": False,
    }
    assert api_client.get(f"/api/projects/{other}/capabilities", headers=headers).status_code == 403
    assert api_client.get(f"/api/projects/{project}", headers=headers).status_code == 200
    assert api_client.get(f"/api/projects/{other}", headers=headers).status_code == 403
    assert api_client.get("/api/groups", headers=headers).status_code == 403
    assert api_client.get(f"/api/projects/{project}/members", headers=headers).status_code == 403
    assert (
        api_client.patch(
            f"/api/projects/{project}", headers=headers, json={"description": "Owner edit"}
        ).status_code
        == 200
    )


def test_content_policy_does_not_supply_project_ownership_capabilities(api_client):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Content only")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    policy = _policy(api_client, admin, permissions={"*": ["*"]})
    entry = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [policy["id"]]},
    )
    assert entry.status_code == 201, entry.text
    capabilities = api_client.get(f"/api/projects/{project}/capabilities", headers=headers)
    assert capabilities.status_code == 200, capabilities.text
    assert capabilities.json() == {
        "can_edit": False,
        "can_delete": False,
        "can_manage_access": False,
    }
    assert (
        api_client.patch(
            f"/api/projects/{project}", headers=headers, json={"name": "Forbidden"}
        ).status_code
        == 403
    )
    administrative = api_client.get(f"/api/projects/{project}/capabilities", headers=admin)
    assert administrative.status_code == 200, administrative.text
    assert all(administrative.json().values())


def test_new_project_creator_gets_owner_without_becoming_instance_admin(api_client):
    admin = _admin_headers(api_client)
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    project = create_project(api_client, headers, "Creator")["id"]
    assert api_client.get(f"/api/projects/{project}", headers=headers).status_code == 200
    members = api_client.get(f"/api/projects/{project}/members", headers=admin).json()
    entry = next(item for item in members if item["user_id"] == user["id"])
    assert entry["owner"] is True
    assert entry["policy_ids"] == []
    assert api_client.get("/api/users", headers=headers).status_code == 403


def test_direct_entry_rejects_ambiguous_or_legacy_grants(api_client):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Validation")["id"]
    user = _create_user(api_client, admin, role="maintainer")
    policy = _policy(api_client, admin)
    for payload in (
        {"user_id": user["id"], "role": "maintainer"},
        {"user_id": user["id"], "policy_ids": []},
        {"user_id": user["id"], "owner": True, "policy_ids": [policy["id"]]},
    ):
        response = api_client.post(f"/api/projects/{project}/members", headers=admin, json=payload)
        assert response.status_code == 422, response.text
