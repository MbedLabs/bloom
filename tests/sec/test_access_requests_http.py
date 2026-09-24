"""A refused user asks the administrators for access, once per resource per day."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api import access_requests as access_requests_api
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models import AuditEvent, User
from app.models.access_request import AccessRequest
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


REQUEST = {"resource_type": "requirement", "resource_ref": "APO-REQ-001", "project_prefix": "APO"}


@pytest.fixture
def sent_mail(monkeypatch):
    """Capture the access request emails instead of sending them."""
    sent = []
    monkeypatch.setattr(
        access_requests_api, "send_access_request_email", lambda **kwargs: sent.append(kwargs)
    )
    return sent


def test_a_request_emails_every_administrator_once_a_day(harness, sent_mail):
    client, session_maker = harness
    _user(session_maker, "boss@example.com", UserRole.admin)
    _user(session_maker, "second@example.com", UserRole.admin)
    _user(session_maker, "member@example.com")
    headers = _login(client, "member@example.com")

    first = client.post("/api/access-requests", json=REQUEST, headers=headers)
    again = client.post("/api/access-requests", json=REQUEST, headers=headers)

    assert first.status_code == 201, first.text
    assert first.json()["status"] == "pending" and first.json()["mail_sent"] is True
    assert again.status_code == 200
    assert again.json()["already_requested"] is True
    assert again.json()["id"] == first.json()["id"]
    assert sorted(mail["to_email"] for mail in sent_mail) == [
        "boss@example.com",
        "second@example.com",
    ]
    mail = sent_mail[0]
    assert mail["requester_email"] == "member@example.com"
    assert mail["resource"] == "APO-REQ-001" and mail["project"] == "APO"
    assert mail["review_link"].endswith("/projects/APO/edit")
    assert mail["request_id"] == first.headers["x-request-id"]
    [event] = _events(session_maker, "access.requested")
    assert event.target_type == "requirement" and event.target_id == "APO-REQ-001"


def test_the_page_learns_a_request_is_pending(harness, sent_mail):
    client, session_maker = harness
    _user(session_maker, "boss@example.com", UserRole.admin)
    _user(session_maker, "member@example.com")
    headers = _login(client, "member@example.com")

    before = client.get("/api/access-requests/mine", params=REQUEST, headers=headers)
    client.post("/api/access-requests", json=REQUEST, headers=headers)
    after = client.get("/api/access-requests/mine", params=REQUEST, headers=headers)

    assert before.status_code == 200 and before.json() is None
    assert after.json()["status"] == "pending"


def test_a_mail_failure_is_reported_and_not_fatal(harness, monkeypatch):
    from app.services.mail_service import MailConfigurationError

    client, session_maker = harness
    _user(session_maker, "boss@example.com", UserRole.admin)
    _user(session_maker, "member@example.com")
    headers = _login(client, "member@example.com")

    def _fail(**kwargs):
        raise MailConfigurationError("SMTP is disabled")

    monkeypatch.setattr(access_requests_api, "send_access_request_email", _fail)
    response = client.post("/api/access-requests", json=REQUEST, headers=headers)

    assert response.status_code == 201
    assert response.json()["mail_sent"] is False


def test_an_administrator_decision_is_recorded_once(harness, sent_mail):
    client, session_maker = harness
    admin = _user(session_maker, "boss@example.com", UserRole.admin)
    member = _user(session_maker, "member@example.com")
    member_headers = _login(client, "member@example.com")
    admin_headers = _login(client, "boss@example.com")
    created = client.post("/api/access-requests", json=REQUEST, headers=member_headers).json()

    listed = client.get(
        "/api/access-requests", params={"project_prefix": "APO"}, headers=admin_headers
    )
    refused_for_member = client.post(
        f"/api/access-requests/{created['id']}/decision",
        json={"decision": "granted"},
        headers=member_headers,
    )
    granted = client.post(
        f"/api/access-requests/{created['id']}/decision",
        json={"decision": "granted"},
        headers=admin_headers,
    )
    twice = client.post(
        f"/api/access-requests/{created['id']}/decision",
        json={"decision": "refused"},
        headers=admin_headers,
    )

    assert [r["requester_email"] for r in listed.json()] == ["member@example.com"]
    assert refused_for_member.status_code == 403
    assert granted.status_code == 200 and granted.json()["status"] == "granted"
    assert twice.status_code == 409
    [event] = _events(session_maker, "access.granted")
    assert event.actor_user_id == admin.id
    assert event.details["requester_user_id"] == member.id


def test_nothing_about_the_resource_is_disclosed(harness, sent_mail):
    client, session_maker = harness
    _user(session_maker, "member@example.com")
    headers = _login(client, "member@example.com")

    response = client.post("/api/access-requests", json=REQUEST, headers=headers)

    assert set(response.json()) == {
        "id",
        "resource_type",
        "resource_ref",
        "project_prefix",
        "status",
        "created_at",
        "decided_at",
        "requester_name",
        "requester_email",
        "already_requested",
        "mail_sent",
    }
    assert response.json()["requester_email"] is None


def test_an_anonymous_client_cannot_request(harness):
    client, _ = harness

    response = client.post("/api/access-requests", json=REQUEST)

    assert response.status_code == 401


def test_a_resource_reference_is_validated(harness, sent_mail):
    client, session_maker = harness
    _user(session_maker, "member@example.com")
    headers = _login(client, "member@example.com")

    response = client.post(
        "/api/access-requests",
        json={**REQUEST, "resource_ref": "../../etc"},
        headers=headers,
    )

    assert response.status_code == 422
