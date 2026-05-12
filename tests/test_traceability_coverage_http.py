import os
import uuid

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _random_prefix() -> str:
    seed = uuid.uuid4().int
    return "".join(_LETTERS[(seed >> (5 * i)) % 26] for i in range(3))


def _admin_headers(api_client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_coverage_gap_report_counts_requirements_by_verification_state(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = uuid.uuid4().hex[:8]
    prefix = _random_prefix()
    create = api_client.post(
        "/api/projects",
        headers=headers,
        json={"name": f"Traceability {suffix}", "prefix": prefix},
    )
    assert create.status_code == 201
    project_id = create.json()["id"]

    uncovered = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": f"Uncovered {suffix}"},
    )
    partial = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": f"Partial {suffix}"},
    )
    covered = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": f"Covered {suffix}"},
    )
    assert uncovered.status_code == 201
    assert partial.status_code == 201
    assert covered.status_code == 201

    draft_tc = api_client.post(
        "/api/test-cases",
        headers=headers,
        json={"project_id": project_id, "title": f"Draft TC {suffix}", "status": "Draft"},
    )
    approved_tc = api_client.post(
        "/api/test-cases",
        headers=headers,
        json={"project_id": project_id, "title": f"Approved TC {suffix}", "status": "Approved"},
    )
    assert draft_tc.status_code == 201
    assert approved_tc.status_code == 201

    for requirement_id, test_case_id in (
        (partial.json()["id"], draft_tc.json()["id"]),
        (covered.json()["id"], approved_tc.json()["id"]),
    ):
        link = api_client.post(
            "/api/links",
            headers=headers,
            json={
                "project_id": project_id,
                "source_type": "TC",
                "source_id": test_case_id,
                "target_type": "REQ",
                "target_id": requirement_id,
                "role": "verifies",
            },
        )
        assert link.status_code == 201

    report = api_client.get(f"/api/traceability/coverage-gaps/{project_id}", headers=headers)
    assert report.status_code == 200
    body = report.json()
    assert body["total_requirements"] == 3
    assert body["uncovered"] == 1
    assert body["partial"] == 1
    assert body["covered"] == 1
    assert body["coverage_percent"] == 33.3
    assert len(body["gaps"]) == 2

    matrix = api_client.get(f"/api/traceability?project_id={project_id}", headers=headers)
    assert matrix.status_code == 200
    statuses = {item["requirement"]["title"]: item["coverage_status"] for item in matrix.json()}
    assert statuses[f"Uncovered {suffix}"] == "Uncovered"
    assert statuses[f"Partial {suffix}"] == "Partial"
    assert statuses[f"Covered {suffix}"] == "Covered"

    filtered = api_client.get(
        f"/api/traceability?project_id={project_id}&coverage_filter=Uncovered",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    sorted_by_coverage = api_client.get(
        f"/api/traceability?project_id={project_id}&sort_by=coverage",
        headers=headers,
    )
    assert sorted_by_coverage.status_code == 200
    assert [item["coverage_status"] for item in sorted_by_coverage.json()] == [
        "Uncovered",
        "Partial",
        "Covered",
    ]

    api_client.delete(f"/api/projects/{project_id}", headers=headers)
