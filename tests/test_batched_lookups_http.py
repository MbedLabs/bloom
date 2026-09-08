import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

from tests.conftest import create_project, unique_suffix

"""Behaviour preserved when per-row lookups were replaced by batched ones."""


def _admin_headers(api_client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _make_test_case(api_client, headers, project_id, title):
    created = api_client.post(
        "/api/test-cases",
        headers=headers,
        json={"project_id": project_id, "title": title},
    )
    assert created.status_code in (200, 201), created.text
    return created.json()["id"]


def test_campaign_rejects_an_unknown_suite_by_id(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Camp Unknown {suffix}")["id"]

    created = api_client.post(
        "/api/campaigns",
        headers=headers,
        json={"project_id": project_id, "name": f"C {suffix}", "suite_ids": [987654]},
    )

    assert created.status_code == 404, created.text
    # The offending id must still be named, not just "a suite was missing".
    assert "987654" in created.text


def test_campaign_rejects_a_suite_from_another_project(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    mine = create_project(api_client, headers, f"Camp Mine {suffix}")["id"]
    theirs = create_project(api_client, headers, f"Camp Theirs {suffix}")["id"]

    foreign_suite = api_client.post(
        "/api/test-suites",
        headers=headers,
        json={"project_id": theirs, "name": f"Foreign {suffix}"},
    )
    assert foreign_suite.status_code in (200, 201), foreign_suite.text
    foreign_id = foreign_suite.json()["id"]

    # The row exists, so only the project check can reject it — the part most
    # easily lost when the per-id query becomes an IN lookup.
    created = api_client.post(
        "/api/campaigns",
        headers=headers,
        json={"project_id": mine, "name": f"C {suffix}", "suite_ids": [foreign_id]},
    )
    assert created.status_code == 404, created.text
    assert str(foreign_id) in created.text


def test_suite_creation_skips_test_cases_from_another_project(api_client: TestClient):
    """Foreign ids are dropped silently here rather than raising, which is the
    existing contract; batching must not turn that into an error or let them in."""
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    mine = create_project(api_client, headers, f"Suite Mine {suffix}")["id"]
    theirs = create_project(api_client, headers, f"Suite Theirs {suffix}")["id"]

    ours = _make_test_case(api_client, headers, mine, f"Ours {suffix}")
    foreign = _make_test_case(api_client, headers, theirs, f"Foreign {suffix}")

    created = api_client.post(
        "/api/test-suites",
        headers=headers,
        json={"project_id": mine, "name": f"S {suffix}", "test_case_ids": [ours, foreign, 987654]},
    )

    assert created.status_code in (200, 201), created.text
    detail = api_client.get(f"/api/test-suites/{created.json()['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["total_items"] == 1


def test_document_section_counts_are_per_document(api_client: TestClient):
    """The list endpoint counts sections for every document in one grouped query.
    A grouped count that lost its key would give each document the same total."""
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Docs {suffix}")["id"]

    doc_ids = []
    for n in range(2):
        created = api_client.post(
            f"/api/projects/{project_id}/documents",
            headers=headers,
            json={"project_id": project_id, "title": f"Doc {n} {suffix}"},
        )
        assert created.status_code in (200, 201), created.text
        doc_ids.append(created.json()["id"])

    first, second = doc_ids
    for n in range(3):
        section = api_client.post(
            f"/api/documents/{first}/sections",
            headers=headers,
            json={"title": f"Section {n} {suffix}", "content": "x"},
        )
        assert section.status_code in (200, 201), section.text

    listed = api_client.get(f"/api/projects/{project_id}/documents", headers=headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    rows = body["items"] if isinstance(body, dict) else body
    counts = {row["id"]: row["section_count"] for row in rows}

    assert counts[first] == 3
    assert counts[second] == 0
