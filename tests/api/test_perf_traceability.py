import pytest
from sqlalchemy import event

from app.core.database import engine
from tests.conftest import create_project


@pytest.fixture
def query_counter():
    class Counter:
        count = 0

    counter = Counter()

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        stmt = statement.strip().upper()
        if not stmt.startswith(
            ("SAVEPOINT", "RELEASE SAVEPOINT", "ROLLBACK TO SAVEPOINT", "BEGIN", "COMMIT")
        ):
            counter.count += 1

    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    yield counter
    event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)


def _admin_headers(api_client) -> dict[str, str]:
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_traceability_matrix_n1_queries(api_client, query_counter):
    headers = _admin_headers(api_client)

    project_id = create_project(api_client, headers, "Perf Traceability")["id"]

    for i in range(15):
        api_client.post(
            "/api/requirements",
            headers=headers,
            json={"project_id": project_id, "title": f"Req {i}"},
        )

    query_counter.count = 0

    matrix = api_client.get(f"/api/traceability?project_id={project_id}", headers=headers)
    assert matrix.status_code == 200

    assert query_counter.count < 10, f"N+1 queries detected! Total queries: {query_counter.count}"


def test_coverage_gaps_n1_queries(api_client, query_counter):
    headers = _admin_headers(api_client)

    project_id = create_project(api_client, headers, "Perf Coverage Gaps")["id"]

    for i in range(15):
        api_client.post(
            "/api/requirements",
            headers=headers,
            json={"project_id": project_id, "title": f"Req {i}"},
        )

    query_counter.count = 0

    report = api_client.get(f"/api/traceability/coverage-gaps/{project_id}", headers=headers)
    assert report.status_code == 200

    assert (
        query_counter.count < 10
    ), f"N+1 queries detected in coverage gaps! Total queries: {query_counter.count}"


def test_requirement_detail_n1_queries(api_client, query_counter):
    headers = _admin_headers(api_client)

    project_id = create_project(api_client, headers, "Perf Req Detail")["id"]

    root_req = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": "Root Req"},
    )
    root_id = root_req.json()["id"]

    for i in range(15):
        api_client.post(
            "/api/requirements",
            headers=headers,
            json={"project_id": project_id, "title": f"Child {i}", "parent_id": root_id},
        )

    query_counter.count = 0

    req_detail = api_client.get(f"/api/requirements/{root_id}", headers=headers)
    assert req_detail.status_code == 200

    assert (
        query_counter.count < 10
    ), f"N+1 queries detected in requirement detail! Total queries: {query_counter.count}"
