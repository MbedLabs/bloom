"""The audit log records security-relevant events with who, where and the outcome."""

import asyncio
import json

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models import AuditEvent, DesignItem, IntegrationSetting, Project, User
from app.models.user import UserRole

PASSWORD = "Correct-Horse-Battery-9"


@pytest.fixture
def harness():
    """An app on a fresh in-memory database, with only the session overridden."""
    from app import models  # noqa: F401

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _create_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    asyncio.run(_create_schema())
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app, base_url="http://test", headers={"user-agent": "audit-test/1.0"})
    try:
        yield client, session_maker
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def _add(session_maker, *rows):
    """Insert rows and return them with their ids."""

    async def _run():
        async with session_maker() as session:
            session.add_all(rows)
            await session.commit()
            return rows

    return asyncio.run(_run())


def _user(session_maker, email, role=UserRole.maintainer):
    return _add(
        session_maker,
        User(
            email=email,
            full_name=email.split("@")[0],
            hashed_password=get_password_hash(PASSWORD),
            role=role,
            is_active=True,
        ),
    )[0]


def _events(session_maker, action=None):
    """All audit events, oldest first, optionally for one action."""

    async def _run():
        async with session_maker() as session:
            query = select(AuditEvent).order_by(AuditEvent.id)
            if action:
                query = query.where(AuditEvent.action == action)
            return list((await session.execute(query)).scalars())

    return asyncio.run(_run())


def _login(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_a_failed_login_is_recorded_although_the_request_fails(harness):
    client, session_maker = harness
    user = _user(session_maker, "someone@example.com")

    response = client.post(
        "/api/auth/login", json={"email": "someone@example.com", "password": "wrong-password-1"}
    )

    assert response.status_code == 401
    [event] = _events(session_maker, "auth.login")
    assert event.outcome == "failure"
    assert event.actor_type == "anonymous"
    assert event.target_type == "user" and event.target_id == str(user.id)
    assert event.request_id == response.headers["x-request-id"]
    assert event.user_agent == "audit-test/1.0"
    assert event.ip
    assert "wrong-password-1" not in json.dumps(event.details)


def test_a_successful_login_names_the_user(harness):
    client, session_maker = harness
    user = _user(session_maker, "member@example.com")

    _login(client, "member@example.com")

    [event] = _events(session_maker, "auth.login")
    assert event.outcome == "success"
    assert event.actor_type == "user" and event.actor_user_id == user.id


def test_a_role_change_records_the_admin_and_both_roles(harness):
    client, session_maker = harness
    admin = _user(session_maker, "admin@example.com", UserRole.admin)
    member = _user(session_maker, "member@example.com")
    headers = _login(client, "admin@example.com")

    response = client.patch(f"/api/users/{member.id}", json={"role": "external"}, headers=headers)

    assert response.status_code == 200, response.text
    [event] = _events(session_maker, "user.role_changed")
    assert event.actor_user_id == admin.id
    assert event.target_id == str(member.id)
    assert event.details == {"from": "maintainer", "to": "external"}


def test_membership_visibility_and_deletion_carry_the_project(harness):
    client, session_maker = harness
    _user(session_maker, "admin@example.com", UserRole.admin)
    member = _user(session_maker, "member@example.com")
    [project] = _add(session_maker, Project(name="Audit project", prefix="AUD"))
    [design] = _add(
        session_maker,
        DesignItem(project_id=project.id, design_id="AUD-DES-001", title="A design"),
    )
    headers = _login(client, "admin@example.com")

    added = client.post(
        f"/api/projects/{project.id}/members",
        json={"user_id": member.id, "role": "maintainer"},
        headers=headers,
    )
    changed = client.patch(
        f"/api/designs/{design.id}", json={"visibility": "customer"}, headers=headers
    )
    deleted = client.delete(f"/api/designs/{design.id}", headers=headers)

    assert (added.status_code, changed.status_code, deleted.status_code) == (201, 200, 204)
    [member_event] = _events(session_maker, "project_member.added")
    [visibility_event] = _events(session_maker, "artefact.visibility_changed")
    [delete_event] = _events(session_maker, "artefact.deleted")
    assert member_event.project_id == project.id
    assert member_event.target_id == str(member.id)
    assert visibility_event.target_id == "AUD-DES-001"
    assert visibility_event.details["to"] == "customer"
    assert delete_event.project_id == project.id
    assert delete_event.target_type == "design"


def test_a_rotated_secret_is_named_but_never_stored(harness):
    client, session_maker = harness
    _user(session_maker, "admin@example.com", UserRole.admin)
    [project] = _add(session_maker, Project(name="Tracker project", prefix="TRK"))
    [setting] = _add(session_maker, IntegrationSetting(project_id=project.id, tracker="jira"))
    headers = _login(client, "admin@example.com")

    response = client.patch(
        f"/api/integrations/settings/{setting.id}",
        json={"token": "very-secret-token-value"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    [event] = _events(session_maker, "integration.updated")
    assert "token" in event.details["fields"]
    assert "very-secret-token-value" not in json.dumps(event.details)


def test_only_administrators_read_the_audit_log(harness):
    client, session_maker = harness
    _user(session_maker, "admin@example.com", UserRole.admin)
    _user(session_maker, "member@example.com")
    member_headers = _login(client, "member@example.com")
    admin_headers = _login(client, "admin@example.com")

    refused = client.get("/api/audit", headers=member_headers)
    page = client.get("/api/audit", params={"action": "auth."}, headers=admin_headers)

    assert refused.status_code == 403
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 2
    assert {item["action"] for item in body["items"]} == {"auth.login"}
    assert body["items"][0]["actor_name"] == "admin"


def _api_routes(routes):
    """Yield every API route, including those of included routers."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        included = getattr(route, "original_router", None)
        if included is not None:
            yield from _api_routes(included.routes)


def test_no_endpoint_changes_or_deletes_an_audit_event():
    methods = {
        method
        for route in _api_routes(app.routes)
        if route.endpoint.__module__ == "app.api.audit"
        for method in route.methods
    }

    assert methods == {"GET"}
