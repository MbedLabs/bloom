"""HTTP tests for dashboard stats (TST-005)."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient


def test_dashboard_stats_shape(api_client: TestClient):
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = api_client.get("/api/dashboard/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "total_projects",
        "total_requirements",
        "total_test_cases",
        "coverage_percent",
        "projects",
    ):
        assert key in data
    assert isinstance(data["projects"], list)

    # Cached second call should match
    resp2 = api_client.get("/api/dashboard/stats", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["total_projects"] == data["total_projects"]
