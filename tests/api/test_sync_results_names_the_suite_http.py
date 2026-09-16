"""Bloom tells Bud which test suites hold the synced test cases."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.test_sync_results_names_the_campaign_http import _admin_headers, _sync
from tests.conftest import create_project, unique_suffix


def _case(api_client: TestClient, headers: dict, project: dict, label: str) -> dict:
    response = api_client.post(
        "/api/test-cases",
        headers=headers,
        json={"project_id": project["id"], "title": f"{label} {unique_suffix()}"},
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def _suite(
    api_client: TestClient, headers: dict, project: dict, label: str, cases: list[dict]
) -> dict:
    response = api_client.post(
        "/api/test-suites",
        headers=headers,
        json={
            "project_id": project["id"],
            "name": f"{label} {unique_suffix()}",
            "test_case_ids": [case["id"] for case in cases],
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def test_sync_names_the_suite_holding_the_synced_case(api_client: TestClient):
    headers = _admin_headers(api_client)
    project = create_project(api_client, headers, f"Suite {unique_suffix()}")
    case = _case(api_client, headers, project, "Case")
    suite = _suite(api_client, headers, project, "Suite", [case])

    body = _sync(api_client, [{"tc_id": case["tc_id"], "status": "Passed"}])

    assert body["updated"] == 1
    assert [s["suite_id"] for s in body["suites"]] == [suite["suite_id"]]
    named = body["suites"][0]
    assert named["id"] == suite["id"]
    assert named["name"] == suite["name"]
    assert named["url"].endswith(f"/projects/{project['prefix']}/suites/{suite['id']}")
    assert named["matched"] == 1
    assert named["size"] == 1


def test_sync_counts_how_many_synced_cases_each_suite_holds(api_client: TestClient):
    headers = _admin_headers(api_client)
    project = create_project(api_client, headers, f"Counts {unique_suffix()}")
    first = _case(api_client, headers, project, "First")
    second = _case(api_client, headers, project, "Second")
    third = _case(api_client, headers, project, "Third")
    executed = _suite(api_client, headers, project, "Executed", [first, second])
    superset = _suite(api_client, headers, project, "Superset", [first, second, third])

    body = _sync(
        api_client,
        [
            {"tc_id": first["tc_id"], "status": "Passed"},
            {"tc_id": second["tc_id"], "status": "Failed"},
        ],
    )

    by_id = {s["id"]: s for s in body["suites"]}
    assert set(by_id) == {executed["id"], superset["id"]}
    assert (by_id[executed["id"]]["matched"], by_id[executed["id"]]["size"]) == (2, 2)
    assert (by_id[superset["id"]]["matched"], by_id[superset["id"]]["size"]) == (2, 3)


def test_a_test_case_in_no_suite_names_none(api_client: TestClient):
    headers = _admin_headers(api_client)
    project = create_project(api_client, headers, f"Loose {unique_suffix()}")
    case = _case(api_client, headers, project, "Case")

    body = _sync(api_client, [{"tc_id": case["tc_id"], "status": "Passed"}])

    assert body["updated"] == 1
    assert body["suites"] == []


def test_an_unmatched_tc_id_names_no_suite(api_client: TestClient):
    headers = _admin_headers(api_client)
    project = create_project(api_client, headers, f"Unmatched {unique_suffix()}")
    case = _case(api_client, headers, project, "Case")
    _suite(api_client, headers, project, "Suite", [case])

    body = _sync(api_client, [{"tc_id": f"NOPE-TC-{unique_suffix()}", "status": "Passed"}])

    assert body["updated"] == 0
    assert body["suites"] == []
