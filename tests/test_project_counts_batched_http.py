import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

from tests.conftest import create_project, unique_suffix

# Every count the project card shows. The list endpoint computes these in bulk
# and the detail endpoint one project at a time; the two must never disagree.
COUNT_KEYS = (
    "requirement_count",
    "test_case_count",
    "campaign_count",
    "design_count",
    "risk_count",
    "change_count",
    "test_concept_count",
    "test_suite_count",
    "defect_count",
    "coverage_percent",
    "uncovered_requirement_count",
)


def _admin_headers(api_client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_listed_counts_match_the_per_project_endpoint(api_client: TestClient):
    """The list endpoint counts every project in one pass, the detail endpoint one
    at a time. They are separate code paths over the same data, so they are
    compared directly here rather than each being asserted against a fixture.
    """
    headers = _admin_headers(api_client)
    suffix = unique_suffix()

    # Two projects with different contents, so a bulk query that mixed rows
    # between projects would show up as a mismatch rather than cancelling out.
    busy = create_project(api_client, headers, f"Counts Busy {suffix}")["id"]
    empty = create_project(api_client, headers, f"Counts Empty {suffix}")["id"]

    for i in range(3):
        created = api_client.post(
            "/api/requirements",
            headers=headers,
            json={"project_id": busy, "title": f"Requirement {i} {suffix}"},
        )
        assert created.status_code in (200, 201), created.text

    listed = api_client.get("/api/projects", headers=headers)
    assert listed.status_code == 200
    by_id = {p["id"]: p for p in listed.json()}

    for project_id in (busy, empty):
        detail = api_client.get(f"/api/projects/{project_id}", headers=headers)
        assert detail.status_code == 200
        detail_body = detail.json()

        for key in COUNT_KEYS:
            assert by_id[project_id][key] == detail_body[key], (
                f"{key} disagrees for project {project_id}: "
                f"list={by_id[project_id][key]} detail={detail_body[key]}"
            )

    # The busy project must actually carry the requirements, so the comparison
    # above is not two zeroes agreeing with each other.
    assert by_id[busy]["requirement_count"] == 3
    assert by_id[empty]["requirement_count"] == 0


def test_counts_are_isolated_between_projects(api_client: TestClient):
    """A grouped query that dropped its GROUP BY would give every project the
    same total, which the equality check above would not catch on its own."""
    headers = _admin_headers(api_client)
    suffix = unique_suffix()

    one = create_project(api_client, headers, f"Iso One {suffix}")["id"]
    two = create_project(api_client, headers, f"Iso Two {suffix}")["id"]

    api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": one, "title": f"Only in one {suffix}"},
    )

    by_id = {p["id"]: p for p in api_client.get("/api/projects", headers=headers).json()}
    assert by_id[one]["requirement_count"] == 1
    assert by_id[two]["requirement_count"] == 0


def test_listing_projects_does_not_issue_a_query_per_project(api_client: TestClient):
    """The cost of the list must not scale with the number of projects.

    Each project card carries eleven counts. Computing them per row meant a
    ten-project dashboard executed 101 sequential statements; this asserts the
    shape of that cost rather than a wall-clock time, so it holds on any machine.
    """
    from sqlalchemy import event

    from app.core.database import engine

    headers = _admin_headers(api_client)
    suffix = unique_suffix()

    def count_list_queries() -> int:
        seen = 0

        def before_cursor_execute(conn, cursor, statement, params, context, executemany):
            nonlocal seen
            seen += 1

        event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
        try:
            assert api_client.get("/api/projects", headers=headers).status_code == 200
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
        return seen

    create_project(api_client, headers, f"Scale A {suffix}")
    baseline = count_list_queries()

    for n in range(4):
        create_project(api_client, headers, f"Scale {n} {suffix}")
    grown = count_list_queries()

    # Four more projects previously meant roughly forty more statements. A small
    # constant increase is tolerated so the assertion does not depend on how many
    # projects other tests happen to have left behind.
    assert grown - baseline <= 2, (
        f"listing grew by {grown - baseline} queries for 4 more projects "
        f"({baseline} -> {grown}); the per-project N+1 has returned"
    )
