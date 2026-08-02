"""Coverage means the same thing wherever it is reported.

The project card, the dashboard and the traceability page each used to compute
coverage themselves, and two of them disagreed with the third: they counted a
requirement as covered as soon as any test case verified it, while traceability
refused to count one whose verifying test cases were all still ``Draft``. The
same project therefore showed a higher percentage on its card than on the page
whose whole job is to report coverage.
"""

import os
import secrets
import string

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest
from fastapi.testclient import TestClient

from app.services.coverage import (
    COVERED,
    PARTIAL,
    UNCOVERED,
    coverage_percent,
    coverage_status,
)


class TestCoverageRule:
    def test_no_test_cases_is_uncovered(self):
        assert coverage_status([]) == UNCOVERED

    def test_only_draft_test_cases_is_partial(self):
        assert coverage_status(["Draft"]) == PARTIAL
        assert coverage_status(["Draft", "Draft"]) == PARTIAL

    def test_one_approved_test_case_covers(self):
        assert coverage_status(["Approved"]) == COVERED
        assert coverage_status(["Draft", "Approved"]) == COVERED

    def test_percentage_is_rounded_to_one_decimal(self):
        assert coverage_percent(1, 3) == 33.3
        assert coverage_percent(2, 4) == 50.0

    def test_percentage_of_an_empty_project_is_zero(self):
        assert coverage_percent(0, 0) == 0


@pytest.fixture
def auth_headers(api_client: TestClient):
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create(api_client: TestClient, headers: dict[str, str], path: str, payload: dict) -> dict:
    response = api_client.post(path, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _verify(api_client, headers, project_id, tc_id, req_id) -> None:
    response = api_client.post(
        "/api/links",
        headers=headers,
        json={
            "project_id": project_id,
            "source_type": "TC",
            "source_id": tc_id,
            "target_type": "REQ",
            "target_id": req_id,
            "role": "verifies",
        },
    )
    assert response.status_code == 201, response.text


def test_all_three_reports_agree(api_client: TestClient, auth_headers: dict[str, str]):
    """One requirement covered, one draft-only, one bare: 33.3% everywhere."""
    from app.core.cache import dashboard_stats_cache

    prefix = "".join(secrets.choice(string.ascii_uppercase) for _ in range(3))
    project = _create(
        api_client,
        auth_headers,
        "/api/projects",
        {"name": f"Coverage Project {prefix}", "prefix": prefix},
    )
    project_id = project["id"]

    covered_req = _create(
        api_client,
        auth_headers,
        "/api/requirements",
        {"project_id": project_id, "title": "Verified requirement"},
    )
    draft_only_req = _create(
        api_client,
        auth_headers,
        "/api/requirements",
        {"project_id": project_id, "title": "Draft-covered requirement"},
    )
    _create(
        api_client,
        auth_headers,
        "/api/requirements",
        {"project_id": project_id, "title": "Untested requirement"},
    )

    approved_tc = _create(
        api_client,
        auth_headers,
        "/api/test-cases",
        {"project_id": project_id, "title": "Approved test case", "status": "Approved"},
    )
    draft_tc = _create(
        api_client,
        auth_headers,
        "/api/test-cases",
        {"project_id": project_id, "title": "Draft test case", "status": "Draft"},
    )

    _verify(api_client, auth_headers, project_id, approved_tc["id"], covered_req["id"])
    _verify(api_client, auth_headers, project_id, draft_tc["id"], draft_only_req["id"])

    gaps = api_client.get(
        f"/api/traceability/coverage-gaps/{project_id}", headers=auth_headers
    ).json()
    assert gaps["total_requirements"] == 3
    assert gaps["covered"] == 1
    assert gaps["partial"] == 1
    assert gaps["uncovered"] == 1
    assert gaps["coverage_percent"] == 33.3

    card = api_client.get(f"/api/projects/{project_id}", headers=auth_headers).json()
    assert card["coverage_percent"] == gaps["coverage_percent"]
    # Everything short of covered is a gap the card must not hide.
    assert card["uncovered_requirement_count"] == gaps["partial"] + gaps["uncovered"]

    dashboard_stats_cache._store.clear()
    dashboard = api_client.get("/api/dashboard/stats", headers=auth_headers).json()
    entry = next(p for p in dashboard["projects"] if p["id"] == project_id)
    assert entry["uncovered_requirement_count"] == card["uncovered_requirement_count"]

    matrix = api_client.get(
        f"/api/traceability?project_id={project_id}", headers=auth_headers
    ).json()
    statuses = {item["requirement"]["req_id"]: item["coverage_status"] for item in matrix}
    assert statuses[covered_req["req_id"]] == COVERED
    assert statuses[draft_only_req["req_id"]] == PARTIAL


def test_draft_only_requirement_is_not_reported_as_covered(
    api_client: TestClient, auth_headers: dict[str, str]
):
    """The regression itself: a draft test case used to satisfy the project card."""
    prefix = "".join(secrets.choice(string.ascii_uppercase) for _ in range(3))
    project = _create(
        api_client,
        auth_headers,
        "/api/projects",
        {"name": f"Draft Only {prefix}", "prefix": prefix},
    )
    project_id = project["id"]

    requirement = _create(
        api_client,
        auth_headers,
        "/api/requirements",
        {"project_id": project_id, "title": "Only draft coverage"},
    )
    test_case = _create(
        api_client,
        auth_headers,
        "/api/test-cases",
        {"project_id": project_id, "title": "Draft", "status": "Draft"},
    )
    _verify(api_client, auth_headers, project_id, test_case["id"], requirement["id"])

    card = api_client.get(f"/api/projects/{project_id}", headers=auth_headers).json()
    assert card["coverage_percent"] == 0
    assert card["uncovered_requirement_count"] == 1


def test_gap_report_no_longer_advertises_missing_link_types(
    api_client: TestClient, auth_headers: dict[str, str]
):
    """`missing_link_types` was never populated, so the branch behind it was dead."""
    prefix = "".join(secrets.choice(string.ascii_uppercase) for _ in range(3))
    project = _create(
        api_client,
        auth_headers,
        "/api/projects",
        {"name": f"Gap Shape {prefix}", "prefix": prefix},
    )
    _create(
        api_client,
        auth_headers,
        "/api/requirements",
        {"project_id": project["id"], "title": "Bare requirement"},
    )

    gaps = api_client.get(
        f"/api/traceability/coverage-gaps/{project['id']}", headers=auth_headers
    ).json()
    assert gaps["gaps"], "a requirement with no test cases is a gap"
    for gap in gaps["gaps"]:
        assert "missing_link_types" not in gap
        assert gap["gap_type"] in {"no_test_cases", "all_draft"}
