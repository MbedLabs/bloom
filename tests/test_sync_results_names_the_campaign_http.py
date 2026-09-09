"""Bloom tells Bud which campaign the synced results reached."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.service_auth import require_bud_sync_token
from app.main import app
from tests.conftest import create_project, unique_suffix


def _admin_headers(api_client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _sync(api_client: TestClient, results: list[dict]) -> dict:
    async def _override():
        return object()

    app.dependency_overrides[require_bud_sync_token] = _override
    try:
        response = api_client.post("/api/campaigns/sync-results", json={"results": results})
    finally:
        app.dependency_overrides.pop(require_bud_sync_token, None)
    assert response.status_code == 200, response.text
    return response.json()


def _campaign_with_one_case(api_client: TestClient, headers: dict, label: str):
    suffix = unique_suffix()
    project = create_project(api_client, headers, f"{label} {suffix}")

    case = api_client.post(
        "/api/test-cases",
        headers=headers,
        json={"project_id": project["id"], "title": f"Case {suffix}"},
    )
    assert case.status_code in (200, 201), case.text

    campaign = api_client.post(
        "/api/campaigns",
        headers=headers,
        json={
            "project_id": project["id"],
            "name": f"Campaign {suffix}",
            "test_case_ids": [case.json()["id"]],
        },
    )
    assert campaign.status_code in (200, 201), campaign.text
    return project, case.json(), campaign.json()


def test_sync_names_the_campaign_the_results_reached(api_client: TestClient):
    headers = _admin_headers(api_client)
    project, case, campaign = _campaign_with_one_case(api_client, headers, "Reached")

    body = _sync(api_client, [{"tc_id": case["tc_id"], "status": "Passed"}])

    assert body["updated"] == 1
    assert [c["campaign_id"] for c in body["campaigns"]] == [campaign["campaign_id"]]
    assert body["campaigns"][0]["id"] == campaign["id"]
    assert body["campaigns"][0]["name"] == campaign["name"]
    assert body["campaigns"][0]["url"].endswith(
        f"/projects/{project['prefix']}/campaigns/{campaign['id']}"
    )


def test_a_test_case_in_no_campaign_names_none(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project = create_project(api_client, headers, f"Loose {suffix}")
    case = api_client.post(
        "/api/test-cases",
        headers=headers,
        json={"project_id": project["id"], "title": f"Case {suffix}"},
    ).json()

    body = _sync(api_client, [{"tc_id": case["tc_id"], "status": "Passed"}])

    assert body["updated"] == 1
    assert body["campaigns"] == []


def test_an_unmatched_tc_id_names_no_campaign(api_client: TestClient):
    headers = _admin_headers(api_client)
    _campaign_with_one_case(api_client, headers, "Unmatched")

    body = _sync(api_client, [{"tc_id": f"NOPE-TC-{unique_suffix()}", "status": "Passed"}])

    assert body["updated"] == 0
    assert body["campaigns"] == []


def test_results_spanning_two_campaigns_name_both(api_client: TestClient):
    headers = _admin_headers(api_client)
    _, first_case, first_campaign = _campaign_with_one_case(api_client, headers, "First")
    _, second_case, second_campaign = _campaign_with_one_case(api_client, headers, "Second")

    body = _sync(
        api_client,
        [
            {"tc_id": first_case["tc_id"], "status": "Passed"},
            {"tc_id": second_case["tc_id"], "status": "Failed"},
        ],
    )

    assert body["updated"] == 2
    assert sorted(c["campaign_id"] for c in body["campaigns"]) == sorted(
        [first_campaign["campaign_id"], second_campaign["campaign_id"]]
    )
