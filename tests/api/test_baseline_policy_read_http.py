"""Baseline reads enforce project policies without changing Owner authority."""

from tests.api.test_groups_http import (
    _admin_headers,
    _create_group,
    _create_user,
    _headers_for,
)
from tests.api.test_project_policy_grants_http import _policy
from tests.conftest import create_project, unique_name


def _baseline(client, admin, project):
    response = client.post(
        "/api/baselines",
        headers=admin,
        json={"project_id": project, "name": unique_name("Baseline")},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _reads(client, headers, project, baseline):
    return [
        client.get("/api/baselines", headers=headers, params={"project_id": project}),
        client.get(f"/api/baselines/{baseline}", headers=headers),
    ]


def test_explicit_project_override_controls_both_baseline_reads(api_client):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Scoped baselines")["id"]
    other = create_project(api_client, admin, "Separate baselines")["id"]
    baseline = _baseline(api_client, admin, project)
    other_baseline = _baseline(api_client, admin, other)
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    baseline_read = _policy(api_client, admin, permissions={"baseline": ["view"]})
    group = _create_group(api_client, admin, baseline_read["id"])
    joined = api_client.post(
        f"/api/groups/{group['id']}/members", headers=admin, json={"user_id": user["id"]}
    )
    assert joined.status_code == 201, joined.text
    admitted = api_client.post(
        f"/api/groups/{group['id']}/grants", headers=admin, json={"project_id": project}
    )
    assert admitted.status_code == 201, admitted.text
    assert [
        response.status_code for response in _reads(api_client, headers, project, baseline)
    ] == [
        200,
        200,
    ]
    requirements_read = _policy(api_client, admin, permissions={"REQ": ["view"]}, types=["REQ"])
    replacement = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "policy_ids": [requirements_read["id"]]},
    )
    assert replacement.status_code == 201, replacement.text
    denied = _reads(api_client, headers, project, baseline)
    assert [response.status_code for response in denied] == [403, 403]
    allowed = api_client.patch(
        f"/api/projects/{project}/members/{replacement.json()['id']}",
        headers=admin,
        json={"policy_ids": [requirements_read["id"], baseline_read["id"]]},
    )
    assert allowed.status_code == 200, allowed.text
    listed, detail = _reads(api_client, headers, project, baseline)
    assert listed.status_code == detail.status_code == 200
    assert baseline in [item["id"] for item in listed.json()]
    assert detail.json()["id"] == baseline
    assert [
        response.status_code for response in _reads(api_client, headers, other, other_baseline)
    ] == [403, 403]
    saved_group = api_client.get(f"/api/groups/{group['id']}", headers=admin)
    assert saved_group.json()["policy_ids"] == [baseline_read["id"]]


def test_baseline_read_group_requires_separate_project_admission(api_client):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Admission required")["id"]
    baseline = _baseline(api_client, admin, project)
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    policy = _policy(api_client, admin, permissions={"baseline": ["view"]})
    group = _create_group(api_client, admin, policy["id"])
    joined = api_client.post(
        f"/api/groups/{group['id']}/members", headers=admin, json={"user_id": user["id"]}
    )
    assert joined.status_code == 201, joined.text
    assert [
        response.status_code for response in _reads(api_client, headers, project, baseline)
    ] == [
        403,
        403,
    ]


def test_admin_and_project_owner_retain_baseline_read_authority(api_client):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Owned baselines")["id"]
    baseline = _baseline(api_client, admin, project)
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    owner = api_client.post(
        f"/api/projects/{project}/members",
        headers=admin,
        json={"user_id": user["id"], "owner": True, "policy_ids": []},
    )
    assert owner.status_code == 201, owner.text
    for actor in (admin, headers):
        listed, detail = _reads(api_client, actor, project, baseline)
        assert listed.status_code == detail.status_code == 200
        assert baseline in [item["id"] for item in listed.json()]
        assert detail.json()["id"] == baseline
