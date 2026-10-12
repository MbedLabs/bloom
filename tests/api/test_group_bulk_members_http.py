"""Bulk membership requests persist together without partial or duplicate additions."""

import pytest

from tests.api.test_groups_http import (
    _admin_headers,
    _create_group,
    _create_policy,
    _create_user,
    _headers_for,
)


def test_bulk_members_persist_without_changing_policies_or_project_admission(api_client):
    headers = _admin_headers(api_client)
    policy = _create_policy(api_client, headers)
    group = _create_group(api_client, headers, policy["id"])
    users = [_create_user(api_client, headers) for _ in range(2)]
    ids = [user["id"] for user in users]
    added = api_client.post(
        f"/api/groups/{group['id']}/members", headers=headers, json={"user_ids": ids}
    )
    assert added.status_code == 201, added.text
    fetched = api_client.get(f"/api/groups/{group['id']}", headers=headers).json()
    assert {member["user_id"] for member in fetched["members"]} == set(ids)
    assert fetched["policy_ids"] == [policy["id"]]
    assert fetched["grants"] == []


def test_bulk_unknown_user_does_not_partially_add_valid_user(api_client):
    headers = _admin_headers(api_client)
    group = _create_group(api_client, headers)
    user = _create_user(api_client, headers)
    response = api_client.post(
        f"/api/groups/{group['id']}/members",
        headers=headers,
        json={"user_ids": [user["id"], 2147483647]},
    )
    assert response.status_code == 404, response.text
    assert api_client.get(f"/api/groups/{group['id']}", headers=headers).json()["members"] == []


@pytest.mark.parametrize("ids", [[], [1, 1], [0], [-1]])
def test_bulk_invalid_selection_is_rejected(api_client, ids):
    headers = _admin_headers(api_client)
    group = _create_group(api_client, headers)
    response = api_client.post(
        f"/api/groups/{group['id']}/members", headers=headers, json={"user_ids": ids}
    )
    assert response.status_code == 422, response.text
    assert api_client.get(f"/api/groups/{group['id']}", headers=headers).json()["members"] == []


def test_bulk_existing_member_is_retained_and_single_duplicate_stays_conflict(api_client):
    headers = _admin_headers(api_client)
    group = _create_group(api_client, headers)
    first, second = [_create_user(api_client, headers) for _ in range(2)]
    route = f"/api/groups/{group['id']}/members"
    assert api_client.post(route, headers=headers, json={"user_id": first["id"]}).status_code == 201
    added = api_client.post(route, headers=headers, json={"user_ids": [first["id"], second["id"]]})
    assert added.status_code == 201, added.text
    repeated = api_client.post(
        route, headers=headers, json={"user_ids": [first["id"], second["id"]]}
    )
    assert repeated.status_code == 201, repeated.text
    assert {m["user_id"] for m in repeated.json()["members"]} == {first["id"], second["id"]}
    assert api_client.post(route, headers=headers, json={"user_id": first["id"]}).status_code == 409


def test_bulk_membership_requires_administrator(api_client):
    headers = _admin_headers(api_client)
    group = _create_group(api_client, headers)
    actor, other = [_create_user(api_client, headers, role="maintainer") for _ in range(2)]
    response = api_client.post(
        f"/api/groups/{group['id']}/members",
        headers=_headers_for(api_client, actor["email"]),
        json={"user_ids": [other["id"]]},
    )
    assert response.status_code == 403, response.text
    assert api_client.get(f"/api/groups/{group['id']}", headers=headers).json()["members"] == []
