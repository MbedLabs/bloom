"""An unreachable issue tracker is answered as such, not as a crash."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import defects as defects_api
from tests.conftest import create_project, unique_suffix


def _admin_headers(api_client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _defect_tracking_an_issue(api_client: TestClient, headers: dict) -> dict:
    suffix = unique_suffix()
    project = create_project(api_client, headers, f"Tracker {suffix}")
    response = api_client.post(
        "/api/defects",
        headers=headers,
        json={
            "project_id": project["id"],
            "title": f"Defect {suffix}",
            "external_tracker": "github",
            "external_repo_full_name": "MbedLabs/bloom",
            "external_issue_number": 7,
            "external_issue_url": "https://github.com/MbedLabs/bloom/issues/7",
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def _refresh(api_client: TestClient, headers: dict, defect_pk: int):
    return api_client.post(
        f"/api/defects/{defect_pk}/refresh-external",
        headers=headers,
        json={"token": "a-token-the-test-never-uses"},
    )


@pytest.mark.parametrize(
    "raised, expected",
    [
        (httpx.ConnectError("no route to host"), 502),
        (httpx.ReadTimeout("timed out"), 504),
        (httpx.ConnectTimeout("timed out"), 504),
        (ValueError("not json"), 502),
    ],
)
def test_a_tracker_that_cannot_be_reached_is_not_a_500(
    api_client: TestClient, monkeypatch, raised, expected
):
    headers = _admin_headers(api_client)
    defect = _defect_tracking_an_issue(api_client, headers)

    async def _fail(*args, **kwargs):
        raise raised

    monkeypatch.setattr(defects_api, "_fetch_github_issue", _fail)

    response = _refresh(api_client, headers, defect["id"])

    assert response.status_code == expected, response.text
    assert response.json()["detail"]


def test_a_tracker_error_names_the_tracker_and_not_the_exception(
    api_client: TestClient, monkeypatch
):
    headers = _admin_headers(api_client)
    defect = _defect_tracking_an_issue(api_client, headers)

    async def _fail(*args, **kwargs):
        raise httpx.ConnectError("no route to host 10.0.0.5")

    monkeypatch.setattr(defects_api, "_fetch_github_issue", _fail)

    response = _refresh(api_client, headers, defect["id"])

    assert "github" in response.json()["detail"]
    assert "10.0.0.5" not in response.text
    assert "ConnectError" not in response.text


def test_a_tracker_that_refuses_is_still_a_bad_gateway(api_client: TestClient, monkeypatch):
    headers = _admin_headers(api_client)
    defect = _defect_tracking_an_issue(api_client, headers)

    async def _refuse(*args, **kwargs):
        raise httpx.HTTPStatusError(
            "401",
            request=httpx.Request("GET", "https://api.github.com"),
            response=httpx.Response(401),
        )

    monkeypatch.setattr(defects_api, "_fetch_github_issue", _refuse)

    response = _refresh(api_client, headers, defect["id"])

    assert response.status_code == 502
    assert "401" in response.json()["detail"]
