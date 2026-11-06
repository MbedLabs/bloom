"""Suites and campaigns are addressed by their public ID in the API; a database ID is a 404."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from tests.api.test_sync_results_names_the_campaign_http import _admin_headers
from tests.api.test_sync_results_names_the_suite_http import _case
from tests.conftest import create_project, unique_suffix


def _created(api_client: TestClient, headers: dict, path: str, body: dict) -> dict:
    response = api_client.post(path, headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_a_suite_is_read_changed_and_deleted_by_its_public_id_only(api_client: TestClient):
    headers = _admin_headers(api_client)
    project = create_project(api_client, headers, f"Suites {unique_suffix()}")
    suite = _created(
        api_client,
        headers,
        "/api/test-suites",
        {"project_id": project["id"], "name": f"Demo {unique_suffix()}"},
    )
    public = f"/api/test-suites/{suite['suite_id']}"
    by_number = f"/api/test-suites/{suite['id']}"

    assert re.fullmatch(rf"{project['prefix']}-TS-\d{{3,}}", suite["suite_id"])
    assert api_client.get(public, headers=headers).json()["id"] == suite["id"]
    for method, body in (("get", None), ("patch", {"name": "Renamed"}), ("delete", None)):
        kwargs = {"headers": headers} if body is None else {"headers": headers, "json": body}
        response = getattr(api_client, method)(by_number, **kwargs)
        assert response.status_code == 404, (method, response.text)
        assert response.json()["detail"] == "Test suite not found"

    renamed = api_client.patch(public, headers=headers, json={"name": "Renamed"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "Renamed"
    assert api_client.delete(public, headers=headers).status_code == 204
    assert api_client.get(public, headers=headers).status_code == 404


def test_suite_items_are_added_and_removed_by_the_test_case_public_id(api_client: TestClient):
    headers = _admin_headers(api_client)
    project = create_project(api_client, headers, f"Items {unique_suffix()}")
    case = _case(api_client, headers, project, "Case")
    suite = _created(
        api_client,
        headers,
        "/api/test-suites",
        {"project_id": project["id"], "name": f"Demo {unique_suffix()}"},
    )
    items = f"/api/test-suites/{suite['suite_id']}/items"

    by_number = api_client.post(f"{items}?test_case_id={case['id']}", headers=headers)
    assert by_number.status_code == 404, by_number.text
    added = api_client.post(f"{items}?test_case_id={case['tc_id']}", headers=headers)
    assert added.status_code == 201, added.text
    assert (added.json()["suite_id"], added.json()["test_case_id"]) == (suite["id"], case["id"])
    again = api_client.post(f"{items}?test_case_id={case['tc_id']}", headers=headers)
    assert again.status_code == 400

    assert api_client.delete(f"{items}/{added.json()['id']}", headers=headers).status_code == 404
    assert api_client.delete(f"{items}/{case['tc_id']}", headers=headers).status_code == 204
    detail = api_client.get(f"/api/test-suites/{suite['suite_id']}", headers=headers).json()
    assert detail["items"] == []
    assert api_client.delete(f"{items}/{case['tc_id']}", headers=headers).status_code == 404


def test_a_test_case_of_another_project_is_not_added_to_a_suite(api_client: TestClient):
    headers = _admin_headers(api_client)
    project = create_project(api_client, headers, f"Mine {unique_suffix()}")
    other = create_project(api_client, headers, f"Other {unique_suffix()}")
    foreign = _case(api_client, headers, other, "Foreign")
    suite = _created(
        api_client,
        headers,
        "/api/test-suites",
        {"project_id": project["id"], "name": f"Demo {unique_suffix()}"},
    )

    response = api_client.post(
        f"/api/test-suites/{suite['suite_id']}/items?test_case_id={foreign['tc_id']}",
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Test case not found in suite project"


def test_a_campaign_and_its_items_are_addressed_by_public_ids_only(api_client: TestClient):
    headers = _admin_headers(api_client)
    project = create_project(api_client, headers, f"Campaigns {unique_suffix()}")
    case = _case(api_client, headers, project, "Case")
    campaign = _created(
        api_client,
        headers,
        "/api/campaigns",
        {"project_id": project["id"], "name": f"Demo {unique_suffix()}"},
    )
    public = f"/api/campaigns/{campaign['campaign_id']}"
    by_number = f"/api/campaigns/{campaign['id']}"

    assert re.fullmatch(rf"{project['prefix']}-CMP-\d{{3,}}", campaign["campaign_id"])
    assert api_client.get(public, headers=headers).json()["id"] == campaign["id"]
    for method, body in (("get", None), ("patch", {"name": "Renamed"}), ("delete", None)):
        kwargs = {"headers": headers} if body is None else {"headers": headers, "json": body}
        response = getattr(api_client, method)(by_number, **kwargs)
        assert response.status_code == 404, (method, response.text)
        assert response.json()["detail"] == "Campaign not found"

    assert (
        api_client.post(f"{public}/items?test_case_id={case['id']}", headers=headers).status_code
        == 404
    )
    added = api_client.post(f"{public}/items?test_case_id={case['tc_id']}", headers=headers)
    assert added.status_code == 201, added.text
    item = f"{public}/items/{case['tc_id']}"
    assert (
        api_client.patch(
            f"{public}/items/{added.json()['id']}", headers=headers, json={"comment": "x"}
        ).status_code
        == 404
    )
    commented = api_client.patch(item, headers=headers, json={"comment": "Checked"})
    assert commented.status_code == 200, commented.text
    assert (commented.json()["id"], commented.json()["comment"]) == (added.json()["id"], "Checked")
    assert api_client.delete(item, headers=headers).status_code == 204
    assert api_client.get(public, headers=headers).json()["items"] == []
    assert api_client.delete(item, headers=headers).status_code == 404

    assert api_client.delete(public, headers=headers).status_code == 204
    assert api_client.get(public, headers=headers).status_code == 404


def test_the_document_address_opens_suites_and_campaigns_by_public_id_only(
    api_client: TestClient,
):
    headers = _admin_headers(api_client)
    project = create_project(api_client, headers, f"Addresses {unique_suffix()}")
    suite = _created(
        api_client,
        headers,
        "/api/test-suites",
        {"project_id": project["id"], "name": f"Demo {unique_suffix()}"},
    )
    campaign = _created(
        api_client,
        headers,
        "/api/campaigns",
        {"project_id": project["id"], "name": f"Demo {unique_suffix()}"},
    )
    case = _case(api_client, headers, project, "Case")
    docs = f"/api/projects/{project['prefix']}/docs"

    for slug, row, key in (
        ("test-suites", suite, "suite_id"),
        ("campaigns", campaign, "campaign_id"),
    ):
        opened = api_client.get(f"{docs}/{slug}/{row[key]}", headers=headers)
        assert opened.status_code == 200, opened.text
        assert (opened.json()["id"], opened.json()["doc_id"]) == (row["id"], row[key])
        assert api_client.get(f"{docs}/{slug}/{row['id']}", headers=headers).status_code == 404

    by_number = api_client.get(f"{docs}/test-cases/{case['id']}", headers=headers)
    assert by_number.status_code == 200, by_number.text
    assert by_number.json()["doc_id"] == case["tc_id"]
