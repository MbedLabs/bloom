"""Every HTTP request leaves one api.request audit event with its actor, client, route, status
and outcome; refused attempts are denied, and repeated refusals from one address are detected."""

import asyncio
import gzip
import json
import re
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.deps import limiter
from app.core.observability import CREATED_BODY_LIMIT, CreatedBody
from app.core.security import create_access_token
from app.main import app
from app.models import (
    AuditEvent,
    DesignItem,
    Notification,
    Project,
    User,
    UserToken,
    UserTokenPurpose,
)
from app.models.user import UserRole
from app.services import audit as audit_service
from app.services.audit import request_outcome, route_template
from tests.sec.test_audit_log_http import (  # noqa: F401
    PASSWORD,
    _add,
    _events,
    _login,
    _user,
    harness,
)

REQUEST = "api.request"


def _requests(session_maker, **match):
    """The api.request events, oldest first, whose attributes or details match."""
    found = []
    for event in _events(session_maker, REQUEST):
        values = {**(event.details or {}), **{k: getattr(event, k) for k in ("outcome", "ip")}}
        if all(values.get(key) == value for key, value in match.items()):
            found.append(event)
    return found


def _one(session_maker, response, **match):
    """The single api.request event of the response, by its request id."""
    events = [
        event
        for event in _requests(session_maker, **match)
        if event.request_id == response.headers["x-request-id"]
    ]
    assert len(events) == 1, events
    return events[0]


def _cli_headers(session_maker, user):
    """Bearer headers of a CLI access token bound to an active refresh row."""
    [refresh] = _add(
        session_maker,
        UserToken(
            user_id=user.id,
            purpose=UserTokenPurpose.refresh,
            token_hash="c" * 64,
            expires_at=datetime.utcnow() + timedelta(days=1),
        ),
    )
    token = create_access_token(
        {
            "sub": str(user.id),
            "type": "user",
            "ver": user.session_version,
            "cli_refresh_id": refresh.id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("client_kind", ["web", "cli"])
def test_each_call_of_a_user_records_actor_client_route_status_and_created_id(harness, client_kind):
    client, session_maker = harness
    admin = _user(session_maker, "admin@example.com", UserRole.admin)
    [project] = _add(session_maker, Project(name="Demo", prefix="PRJ"))
    headers = (
        _login(client, admin.email) if client_kind == "web" else _cli_headers(session_maker, admin)
    )

    read = client.get(f"/api/projects/{project.id}", headers=headers)
    created = client.post(
        "/api/requirements",
        json={"project_id": project.id, "title": "Logged", "description": "x" * 2000},
        headers={**headers, "Accept-Encoding": "gzip"},
    )
    requirement = created.json()
    assert created.headers["content-encoding"] == "gzip"
    changed = client.patch(
        f"/api/requirements/{requirement['id']}", json={"title": "Renamed"}, headers=headers
    )
    deleted = client.delete(f"/api/requirements/{requirement['id']}", headers=headers)

    assert (read.status_code, created.status_code, changed.status_code, deleted.status_code) == (
        200,
        201,
        200,
        204,
    )
    expected = [
        (read, "GET", "/api/projects/{project_id}", 200, "project", str(project.id)),
        (created, "POST", "/api/requirements", 201, None, None),
        (
            changed,
            "PATCH",
            "/api/requirements/{requirement_id}",
            200,
            "requirement",
            str(requirement["id"]),
        ),
        (
            deleted,
            "DELETE",
            "/api/requirements/{requirement_id}",
            204,
            "requirement",
            str(requirement["id"]),
        ),
    ]
    for response, method, route, status, target_type, target_id in expected:
        event = _one(session_maker, response, method=method, route=route, status=status)
        assert event.actor_type == "user"
        assert event.actor_user_id == admin.id
        assert event.details["client"] == client_kind
        assert event.details["auth"] == "bearer"
        assert event.outcome == "success"
        assert event.target_type == target_type
        assert event.target_id == target_id
        assert event.ip
        assert event.user_agent == "audit-test/1.0"
    created_event = _one(session_maker, created)
    assert created_event.details["created_id"] == requirement["id"]
    assert created_event.details["created_doc_id"] == requirement["req_id"]
    assert _one(session_maker, read).project_id == project.id


def test_a_service_credential_call_names_the_credential(harness, monkeypatch):
    monkeypatch.setattr(settings, "SERVICE_TOKEN_PEPPER", "p" * 40)
    client, session_maker = harness
    _user(session_maker, "admin@example.com", UserRole.admin)
    _add(session_maker, Project(name="Demo", prefix="PRJ"))
    admin_headers = _login(client, "admin@example.com")
    issued = client.post(
        "/api/service-credentials", json={"name": "Bud sync"}, headers=admin_headers
    )
    assert issued.status_code == 201, issued.text
    credential_id = issued.json()["id"]
    service = {"Authorization": f"Bearer {issued.json()['token']}"}

    mailbox = client.get("/api/bud/report-requests", params={"after_id": 0}, headers=service)
    published = client.post(
        "/api/bud/test-reports",
        json={"project_prefix": "PRJ", "bud_run_id": 7, "run_name": "Nightly"},
        headers=service,
    )

    assert (mailbox.status_code, published.status_code) == (200, 201), published.text
    read_event = _one(session_maker, mailbox, route="/api/bud/report-requests")
    created_event = _one(session_maker, published, method="POST", status=201)
    for event in (read_event, created_event):
        assert event.actor_type == "service"
        assert event.actor_user_id is None
        assert event.details["service_credential_id"] == credential_id
        assert "client" not in event.details
    assert read_event.details["query"] == ["after_id"]
    assert created_event.details["created_id"] == published.json()["document_id"]
    assert created_event.details["created_doc_id"] == published.json()["doc_id"]
    issued_event = _one(session_maker, issued)
    assert issued_event.details["created_id"] == credential_id
    assert issued.json()["token"] not in json.dumps(issued_event.details)


def test_refused_attempts_are_denied_with_the_address(harness):
    client, session_maker = harness
    _user(session_maker, "admin@example.com", UserRole.admin)
    _user(session_maker, "member@example.com")
    [project] = _add(session_maker, Project(name="Demo", prefix="PRJ"))
    [design] = _add(
        session_maker,
        DesignItem(project_id=project.id, design_id="PRJ-DES-001", title="Hidden design"),
    )
    member = _login(client, "member@example.com")

    forged = client.get("/api/projects", headers={"Authorization": "Bearer forged.token.value"})
    forbidden = client.get(f"/api/projects/{project.id}", headers=member)
    hidden = client.get(f"/api/designs/{design.id}", headers=member)
    missing = client.get("/api/designs/999999", headers=member)

    assert [r.status_code for r in (forged, forbidden, hidden, missing)] == [401, 403, 404, 404]
    for response in (forged, forbidden, hidden):
        event = _one(session_maker, response)
        assert event.outcome == "denied"
        assert event.ip
    assert _one(session_maker, forged).actor_type == "anonymous"
    assert _one(session_maker, forbidden).project_id == project.id
    assert _one(session_maker, hidden).target_id == str(design.id)
    assert _one(session_maker, missing).outcome == "failure"


def test_a_rate_limited_request_is_denied(harness, monkeypatch):
    client, session_maker = harness
    limiter.reset()
    monkeypatch.setattr(limiter, "enabled", True)
    try:
        answers = [
            client.post(
                "/api/auth/login", json={"email": "nobody@example.com", "password": "Wrong-1234"}
            )
            for _ in range(11)
        ]
    finally:
        limiter.reset()

    assert answers[-1].status_code == 429
    event = _one(session_maker, answers[-1], route="/api/auth/login")
    assert event.outcome == "denied"
    assert event.ip
    assert answers[0].status_code == 401
    assert _one(session_maker, answers[0]).outcome == "denied"


def test_repeated_refusals_from_one_address_are_detected_once_per_window(harness):
    client, session_maker = harness
    forged = {"Authorization": "Bearer forged"}

    for _ in range(19):
        assert client.get("/api/projects", headers=forged).status_code == 401
    assert _events(session_maker, "security.repeated_refusals") == []
    for _ in range(6):
        client.get("/api/projects", headers=forged)

    [detected] = _events(session_maker, "security.repeated_refusals")
    assert detected.ip
    assert detected.outcome == "denied"
    assert detected.details == {
        "address": detected.ip,
        "count": settings.AUDIT_REFUSAL_THRESHOLD,
        "window_minutes": settings.AUDIT_REFUSAL_WINDOW_MINUTES,
    }
    assert len(_requests(session_maker, outcome="denied")) == 25


def test_refusals_outside_the_window_do_not_count(harness, monkeypatch):
    client, session_maker = harness
    monkeypatch.setattr(settings, "AUDIT_REFUSAL_THRESHOLD", 3)
    _add(
        session_maker,
        *[
            AuditEvent(
                occurred_at=datetime.utcnow() - timedelta(minutes=11),
                actor_type="anonymous",
                action=REQUEST,
                ip="testclient",
                outcome="denied",
            )
            for _ in range(5)
        ],
    )

    client.get("/api/projects", headers={"Authorization": "Bearer forged"})
    assert _events(session_maker, "security.repeated_refusals") == []
    client.get("/api/projects", headers={"Authorization": "Bearer forged"})
    client.get("/api/projects", headers={"Authorization": "Bearer forged"})
    assert len(_events(session_maker, "security.repeated_refusals")) == 1


def test_no_event_holds_a_password_token_body_or_query_value(harness):
    client, session_maker = harness
    _user(session_maker, "admin@example.com", UserRole.admin)
    headers = _login(client, "admin@example.com")
    token = headers["Authorization"].split()[1]
    client.post(
        "/api/auth/login", json={"email": "admin@example.com", "password": "Not-The-Password-9"}
    )

    searched = client.get(
        "/api/projects", params={"search": "confidential-search-text"}, headers=headers
    )

    assert searched.status_code == 200
    assert _one(session_maker, searched).details["query"] == ["search"]
    stored = json.dumps(
        [
            {column: str(getattr(event, column)) for column in AuditEvent.__table__.columns.keys()}
            for event in _events(session_maker)
        ]
    )
    for secret in (PASSWORD, "Not-The-Password-9", token, "confidential-search-text"):
        assert secret not in stored


def test_health_probes_and_metrics_scrapes_are_recorded(harness):
    client, session_maker = harness

    health = client.get("/api/health")
    metrics = client.get("/api/metrics")

    for response, route in ((health, "/api/health"), (metrics, "/api/metrics")):
        event = _one(session_maker, response, route=route, method="GET")
        assert event.actor_type == "anonymous"
        assert event.details["auth"] == "none"
        assert event.details["status"] == response.status_code
        assert event.details["duration_ms"] >= 0


def test_an_audit_write_failure_leaves_the_response_unchanged(harness, monkeypatch, caplog):
    client, session_maker = harness

    async def _unavailable(scope):
        raise OperationalError("INSERT", {}, Exception("database unavailable"))

    monkeypatch.setattr(audit_service, "_open_session", _unavailable)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert _events(session_maker, REQUEST) == []
    assert "api.request could not be recorded" in caplog.text


def test_the_audit_log_filters_by_actor_type_address_request_and_status(harness):
    client, session_maker = harness
    _user(session_maker, "admin@example.com", UserRole.admin)
    headers = _login(client, "admin@example.com")
    refused = client.get("/api/projects", headers={"Authorization": "Bearer forged"})
    address = _one(session_maker, refused).ip

    def _page(**params):
        response = client.get("/api/audit", params={"limit": 500, **params}, headers=headers)
        assert response.status_code == 200, response.text
        return response.json()["items"]

    [by_request] = _page(request_id=refused.headers["x-request-id"])
    assert by_request["details"]["status"] == 401
    assert {item["details"]["status"] for item in _page(status=401)} == {401}
    assert {item["actor_type"] for item in _page(actor_type="anonymous")} == {"anonymous"}
    assert {item["ip"] for item in _page(ip=address)} == {address}
    assert _page(ip="203.0.113.9") == []
    assert {item["action"] for item in _page(action="api.", outcome="denied")} == {REQUEST}


def test_route_templates_carry_their_prefix_and_outcomes_follow_the_status():
    class _Route:
        path_format = "/{project_id}/things/{thing_id}"
        path_regex = re.compile(r"^/(?P<project_id>[^/]+)/things/(?P<thing_id>[^/]+)$")

    assert (
        route_template({"route": _Route(), "path": "/api/projects/3/things/9"})
        == "/api/projects/{project_id}/things/{thing_id}"
    )
    assert route_template({"path": "/nowhere"}) == "unmatched"
    assert [request_outcome(code) for code in (200, 302, 401, 403, 404, 429, 500)] == [
        "success",
        "success",
        "denied",
        "denied",
        "failure",
        "denied",
        "failure",
    ]
    assert request_outcome(404, refused=True) == "denied"


def test_a_created_body_is_read_plain_or_gzip_and_bounded():
    plain = CreatedBody(gzipped=False)
    plain.feed(b'{"id": 4, ')
    plain.feed(b'"doc_id": "PRJ-DOC-004"}')
    packed = CreatedBody(gzipped=True)
    packed.feed(gzip.compress(b'{"id": 5}'))
    large = CreatedBody(gzipped=False)
    large.feed(b"x" * (CREATED_BODY_LIMIT + 1))
    broken = CreatedBody(gzipped=True)
    broken.feed(b"not gzip")

    assert plain.parsed() == {"id": 4, "doc_id": "PRJ-DOC-004"}
    assert packed.parsed() == {"id": 5}
    assert large.parsed() is None
    assert broken.parsed() is None


def test_the_actor_set_by_a_dependency_reaches_the_middleware(harness):
    client, session_maker = harness
    member = _user(session_maker, "member@example.com")
    headers = _login(client, "member@example.com")

    response = client.get("/api/auth/me", headers=headers)

    event = _one(session_maker, response, route="/api/auth/me")
    assert (event.actor_type, event.actor_user_id) == ("user", member.id)


def test_a_cors_preflight_is_answered_and_recorded(harness):
    client, session_maker = harness
    origin = settings.CORS_ORIGINS[0]

    response = client.options(
        "/api/projects",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["x-request-id"]
    event = _one(session_maker, response, method="OPTIONS", status=200)
    assert event.outcome == "success"
    assert event.actor_type == "anonymous"


def test_a_cors_answer_keeps_its_headers_with_the_request_id(harness):
    client, session_maker = harness
    origin = settings.CORS_ORIGINS[0]

    response = client.get("/api/health", headers={"Origin": origin})

    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["x-request-id"]
    assert _one(session_maker, response, route="/api/health").outcome == "success"


@pytest.fixture
def exploding_route(harness):
    """A route on the application that raises an unhandled error, on the harness database."""
    path = "/api/__audit_boom__"

    @app.get(path)
    async def _boom():
        raise RuntimeError("audit boom")

    yield path
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != path]


def test_an_unhandled_error_leaves_a_failure_event_with_status_500(harness, exploding_route):
    _, session_maker = harness
    client = TestClient(app, base_url="http://test", raise_server_exceptions=False)

    response = client.get(exploding_route)

    assert response.status_code == 500
    [event] = _requests(session_maker, route=exploding_route, status=500, method="GET")
    assert event.outcome == "failure"
    assert event.request_id
    assert "audit boom" not in json.dumps(event.details)


def test_a_500_quotes_the_supplied_request_id_of_its_audit_event(harness, exploding_route):
    _, session_maker = harness
    client = TestClient(app, base_url="http://test", raise_server_exceptions=False)

    response = client.get(exploding_route, headers={"X-Request-ID": "report-me-500"})

    assert response.status_code == 500
    body = response.json()
    assert response.headers["x-request-id"] == "report-me-500"
    assert body["request_id"] == "report-me-500"
    assert "Quote reference report-me-500 when reporting this." in body["detail"]
    [event] = _requests(session_maker, route=exploding_route, status=500)
    assert event.request_id == "report-me-500"


def test_a_deactivated_account_is_denied_and_named(harness):
    client, session_maker = harness
    user = _user(session_maker, "former@example.com")
    token = create_access_token({"sub": str(user.id), "type": "user", "ver": user.session_version})

    async def _deactivate():
        async with session_maker() as session:
            await session.execute(update(User).where(User.id == user.id).values(is_active=False))
            await session.commit()

    asyncio.run(_deactivate())
    response = client.get("/api/projects", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    event = _one(session_maker, response)
    assert (event.actor_type, event.actor_user_id, event.outcome) == ("user", user.id, "denied")


def test_another_users_notification_is_a_denied_404(harness):
    client, session_maker = harness
    owner = _user(session_maker, "owner@example.com")
    _user(session_maker, "other@example.com")
    [notification] = _add(
        session_maker,
        Notification(user_id=owner.id, event_type="comment", title="For the owner only"),
    )
    other = _login(client, "other@example.com")

    hidden = client.post(f"/api/notifications/{notification.id}/read", headers=other)
    missing = client.post("/api/notifications/999999/read", headers=other)

    assert (hidden.status_code, missing.status_code) == (404, 404)
    assert _one(session_maker, hidden).outcome == "denied"
    assert _one(session_maker, missing).outcome == "failure"


def test_a_404_is_denied_to_an_anonymous_caller_and_a_failure_to_a_signed_in_user(harness):
    client, session_maker = harness
    _user(session_maker, "member@example.com")
    member = _login(client, "member@example.com")

    scanned = client.get("/api/.env")
    unknown_route = client.get("/api/no-such-thing", headers=member)
    missing_row = client.get("/api/designs/999999", headers=member)

    assert [r.status_code for r in (scanned, unknown_route, missing_row)] == [404, 404, 404]
    scan = _one(session_maker, scanned)
    assert (scan.actor_type, scan.outcome, scan.details["route"]) == (
        "anonymous",
        "denied",
        "unmatched",
    )
    unchecked = _one(session_maker, unknown_route)
    assert (unchecked.actor_type, unchecked.details["auth"], unchecked.outcome) == (
        "anonymous",
        "bearer",
        "denied",
    )
    signed_in = _one(session_maker, missing_row)
    assert (signed_in.actor_type, signed_in.outcome) == ("user", "failure")
    assert request_outcome(404, anonymous=True) == "denied"
    assert request_outcome(404) == "failure"
