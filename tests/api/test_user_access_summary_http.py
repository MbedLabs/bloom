"""An Admin reads a user's groups and project access by name only."""

from tests.api.test_groups_http import (
    _admin_headers,
    _create_group,
    _create_user,
    _headers_for,
)
from tests.api.test_project_policy_grants_http import _policy
from tests.conftest import create_project, unique_name


def _summary(api_client, headers, user_id):
    return api_client.get(f"/api/users/{user_id}/access-summary", headers=headers)


def test_summary_lists_groups_and_each_project_with_the_groups_of_its_report(api_client):
    admin = _admin_headers(api_client)
    user = _create_user(api_client, admin, role="maintainer")
    policy = _policy(api_client, admin)
    granted = _create_group(api_client, admin, policy_id=policy["id"])
    other = _create_group(api_client, admin, policy_id=policy["id"])
    bundle = _create_group(api_client, admin, policy_id=policy["id"])
    for group in (granted, other):
        added = api_client.post(
            f"/api/groups/{group['id']}/members", headers=admin, json={"user_id": user["id"]}
        )
        assert added.status_code == 201, added.text
    created = [create_project(api_client, admin, unique_name(prefix)) for prefix in "ABC"]
    via_group, via_bundle, owned = (project["id"] for project in created)
    names = [project["name"] for project in created]
    grant = api_client.post(
        f"/api/groups/{granted['id']}/grants", headers=admin, json={"project_id": via_group}
    )
    assert grant.status_code == 201, grant.text
    for body in (
        {"project": via_bundle, "json": {"user_id": user["id"], "policy_group_id": bundle["id"]}},
        {"project": owned, "json": {"user_id": user["id"], "owner": True, "policy_ids": []}},
    ):
        entry = api_client.post(
            f"/api/projects/{body['project']}/members", headers=admin, json=body["json"]
        )
        assert entry.status_code == 201, entry.text

    response = _summary(api_client, admin, user["id"])

    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["every_project"] is False
    assert summary["groups"] == sorted([granted["name"], other["name"]])
    assert summary["projects"] == [
        {
            "project_id": via_group,
            "project_name": names[0],
            "owner": False,
            "groups": sorted([granted["name"], other["name"]]),
            "direct": False,
        },
        {
            "project_id": via_bundle,
            "project_name": names[1],
            "owner": False,
            "groups": [bundle["name"]],
            "direct": False,
        },
        {
            "project_id": owned,
            "project_name": names[2],
            "owner": True,
            "groups": [],
            "direct": False,
        },
    ]
    assert policy["name"] not in response.text


def test_direct_policies_are_labelled_direct(api_client):
    admin = _admin_headers(api_client)
    user = _create_user(api_client, admin, role="maintainer")
    project = create_project(api_client, admin, unique_name("Direct"))["id"]
    policy = _policy(api_client, admin)
    entry = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [policy["id"]]},
    )
    assert entry.status_code == 201, entry.text

    projects = _summary(api_client, admin, user["id"]).json()["projects"]

    assert [(item["project_id"], item["groups"], item["direct"]) for item in projects] == [
        (project, [], True)
    ]


def test_user_without_access_has_empty_lists_and_admin_has_every_project(api_client):
    admin = _admin_headers(api_client)
    user = _create_user(api_client, admin, role="maintainer")
    assert _summary(api_client, admin, user["id"]).json() == {
        "every_project": False,
        "groups": [],
        "projects": [],
    }
    other_admin = _create_user(api_client, admin, role="admin")
    assert _summary(api_client, admin, other_admin["id"]).json()["every_project"] is True


def test_summary_is_admin_only_and_unknown_users_are_not_found(api_client):
    admin = _admin_headers(api_client)
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    assert _summary(api_client, headers, user["id"]).status_code == 403
    assert _summary(api_client, admin, 999999).status_code == 404
