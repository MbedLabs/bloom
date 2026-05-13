import pytest
from sqlalchemy import event

from app.core.database import engine


@pytest.fixture
def query_counter():
    class Counter:
        count = 0

    counter = Counter()

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        # Ignore transaction management overhead
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


import uuid

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _random_prefix() -> str:
    seed = uuid.uuid4().int
    return "".join(_LETTERS[(seed >> (5 * i)) % 26] for i in range(3))


def test_traceability_matrix_n1_queries(api_client, query_counter):
    headers = _admin_headers(api_client)

    # Create project
    prefix = _random_prefix()
    create = api_client.post(
        "/api/projects",
        headers=headers,
        json={"name": f"Perf Traceability {prefix}", "prefix": prefix},
    )
    project_id = create.json()["id"]

    # Create 15 requirements
    for i in range(15):
        api_client.post(
            "/api/requirements",
            headers=headers,
            json={"project_id": project_id, "title": f"Req {i}"},
        )

    # Reset counter after setup
    query_counter.count = 0

    matrix = api_client.get(f"/api/traceability?project_id={project_id}", headers=headers)
    assert matrix.status_code == 200

    # Ideal is 1-3 queries (Project, Requirements, Links).
    # If N+1, it'll be > 15. We assert < 10 to give headroom but catch N+1.
    assert query_counter.count < 10, f"N+1 queries detected! Total queries: {query_counter.count}"


def test_coverage_gaps_n1_queries(api_client, query_counter):
    headers = _admin_headers(api_client)

    # Create project
    prefix = _random_prefix()
    create = api_client.post(
        "/api/projects",
        headers=headers,
        json={"name": f"Perf Coverage Gaps {prefix}", "prefix": prefix},
    )
    project_id = create.json()["id"]

    # Create 15 requirements
    for i in range(15):
        api_client.post(
            "/api/requirements",
            headers=headers,
            json={"project_id": project_id, "title": f"Req {i}"},
        )

    # Reset counter after setup
    query_counter.count = 0

    report = api_client.get(f"/api/traceability/coverage-gaps/{project_id}", headers=headers)
    assert report.status_code == 200

    assert (
        query_counter.count < 10
    ), f"N+1 queries detected in coverage gaps! Total queries: {query_counter.count}"


def test_requirement_detail_n1_queries(api_client, query_counter):
    headers = _admin_headers(api_client)

    # Create project
    prefix = _random_prefix()
    create = api_client.post(
        "/api/projects",
        headers=headers,
        json={"name": f"Perf Req Detail {prefix}", "prefix": prefix},
    )
    project_id = create.json()["id"]

    # Create root requirement
    root_req = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": "Root Req"},
    )
    root_id = root_req.json()["id"]

    # Create 15 children for the root requirement
    for i in range(15):
        api_client.post(
            "/api/requirements",
            headers=headers,
            json={"project_id": project_id, "title": f"Child {i}", "parent_id": root_id},
        )

    # Reset counter after setup
    query_counter.count = 0

    req_detail = api_client.get(f"/api/requirements/{root_id}", headers=headers)
    assert req_detail.status_code == 200

    # Assert query count is small (1-3) and not O(N) where N is number of children
    assert (
        query_counter.count < 10
    ), f"N+1 queries detected in requirement detail! Total queries: {query_counter.count}"
