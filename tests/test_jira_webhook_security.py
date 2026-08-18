"""Jira webhook: signature enforcement, replay protection, and status mapping.

Jira is held to the same contract as the GitHub and GitLab webhooks — a
configured secret makes signature verification mandatory, and a delivery
identifier is consumed once — and it additionally targets change requests, not
only defects.
"""

import hashlib
import hmac
import json

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import integrations
from app.core.database import Base, get_db
from app.models import (
    ChangeRequest,
    ChangeRequestSyncEvent,
    Defect,
    DefectSyncEvent,
    IntegrationSetting,
    Project,
)
from app.services.integration_secrets import encrypt_integration_secret

SECRET = "jira-hook-secret-123"


@pytest_asyncio.fixture
async def env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with maker() as setup:
        project = Project(name="Alpha", prefix="ALP")
        setup.add(project)
        await setup.flush()
        setup.add(
            Defect(
                project_id=project.id,
                defect_id="ALP-DEF-001",
                title="Broken login",
                status="Open",
                external_tracker="jira",
                external_repo_full_name="PROJ",
                external_issue_number=42,
            )
        )
        setup.add(
            ChangeRequest(
                project_id=project.id,
                change_id="ALP-CR-001",
                title="Swap the sensor",
                status="Submitted",
                external_tracker="jira",
                external_repo_full_name="PROJ",
                external_issue_number=99,
            )
        )
        setup.add(
            IntegrationSetting(
                project_id=project.id,
                tracker="jira",
                base_url="https://acme.atlassian.net",
                account_email="bot@acme.test",
                webhook_secret=encrypt_integration_secret(SECRET),
                enabled=True,
            )
        )
        await setup.commit()

    app = FastAPI()
    app.include_router(integrations.router, prefix="/api/integrations")

    async def override_get_db():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, maker
    await engine.dispose()


def _payload(issue_key: str, category: str = "done", status_name: str = "Done") -> bytes:
    return json.dumps(
        {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": issue_key,
                "fields": {
                    "status": {"name": status_name, "statusCategory": {"key": category}},
                },
            },
        }
    ).encode()


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def _post(client, body: bytes, *, signature=None, delivery="d-1"):
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Hub-Signature"] = signature
    if delivery is not None:
        headers["X-Atlassian-Webhook-Identifier"] = delivery
    return client.post("/api/integrations/jira/webhook", content=body, headers=headers)


async def _defect_status(maker) -> str:
    async with maker() as session:
        row = (
            await session.execute(select(Defect).where(Defect.defect_id == "ALP-DEF-001"))
        ).scalar_one()
        return row.status


async def _change_status(maker) -> str:
    async with maker() as session:
        row = (
            await session.execute(
                select(ChangeRequest).where(ChangeRequest.change_id == "ALP-CR-001")
            )
        ).scalar_one()
        return row.status


def test_rejects_missing_signature(env):
    """Omitting the header must not bypass verification."""
    client, _ = env
    response = _post(client, _payload("PROJ-42"), signature=None)
    assert response.status_code == 403


def test_rejects_wrong_signature(env):
    client, _ = env
    response = _post(client, _payload("PROJ-42"), signature="sha256=deadbeef")
    assert response.status_code == 403


def test_rejects_signature_over_different_body(env):
    """A signature lifted from another delivery must not validate."""
    client, _ = env
    response = _post(client, _payload("PROJ-42"), signature=_sign(_payload("PROJ-999")))
    assert response.status_code == 403


def test_requires_a_delivery_identifier(env):
    client, _ = env
    body = _payload("PROJ-42")
    response = _post(client, body, signature=_sign(body), delivery=None)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_valid_signature_closes_the_linked_defect(env):
    client, maker = env
    body = _payload("PROJ-42")

    response = _post(client, body, signature=_sign(body))

    assert response.status_code == 200
    assert response.json()["target"] == "defect"
    assert await _defect_status(maker) == "Closed"


@pytest.mark.asyncio
async def test_valid_signature_closes_the_linked_change_request(env):
    client, maker = env
    body = _payload("PROJ-99")

    response = _post(client, body, signature=_sign(body), delivery="d-cr")

    assert response.status_code == 200
    assert response.json()["target"] == "change_request"
    assert await _change_status(maker) == "Closed"


@pytest.mark.asyncio
async def test_status_category_maps_to_bloom_status(env):
    client, maker = env
    body = _payload("PROJ-42", category="indeterminate", status_name="In Review")

    assert _post(client, body, signature=_sign(body)).status_code == 200
    assert await _defect_status(maker) == "In Progress"


@pytest.mark.asyncio
async def test_replayed_delivery_is_ignored(env):
    """The same delivery id must apply once, so a captured request cannot be replayed."""
    client, maker = env
    body = _payload("PROJ-42")
    assert _post(client, body, signature=_sign(body), delivery="same").status_code == 200

    # Flip the defect back, then replay the identical signed request.
    async with maker() as session:
        row = (
            await session.execute(select(Defect).where(Defect.defect_id == "ALP-DEF-001"))
        ).scalar_one()
        row.status = "Open"
        await session.commit()

    replay = _post(client, body, signature=_sign(body), delivery="same")

    assert replay.json()["status"] == "duplicate"
    assert await _defect_status(maker) == "Open"


def test_unlinked_issue_is_not_found(env):
    client, _ = env
    body = _payload("PROJ-777")
    assert _post(client, body, signature=_sign(body)).status_code == 404


def test_non_issue_events_are_ignored(env):
    client, _ = env
    body = json.dumps({"webhookEvent": "jira:worklog_updated"}).encode()
    response = _post(client, body, signature=_sign(body))
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_malformed_issue_key_is_ignored(env):
    client, _ = env
    body = _payload("NOTAKEY")
    response = _post(client, body, signature=_sign(body))
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_rejected_delivery_records_no_successful_event(env):
    """A spoofed delivery must leave no successful sync event on either log.

    The rejection rolls the request transaction back, so the attempted
    ``signature_failed`` row goes with it; what matters is that nothing is
    recorded as having succeeded.
    """
    client, maker = env
    _post(client, _payload("PROJ-42"), signature="sha256=bad")
    _post(client, _payload("PROJ-99"), signature="sha256=bad", delivery="d-cr")

    async with maker() as session:
        defect_events = (await session.execute(select(DefectSyncEvent))).scalars().all()
        change_events = (await session.execute(select(ChangeRequestSyncEvent))).scalars().all()

    assert [e for e in defect_events if e.success] == []
    assert [e for e in change_events if e.success] == []


@pytest.mark.asyncio
async def test_sync_events_route_to_the_matching_log(env):
    """Defect events and change-request events must land in their own tables."""
    _, maker = env
    async with maker() as session:
        integrations._log_target_sync_event(session, "defect", 1, "inbound", "jira", "probe_defect")
        integrations._log_target_sync_event(
            session, "change_request", 1, "inbound", "jira", "probe_change"
        )
        await session.commit()

    async with maker() as session:
        defect_events = (await session.execute(select(DefectSyncEvent))).scalars().all()
        change_events = (await session.execute(select(ChangeRequestSyncEvent))).scalars().all()

    assert [e.event_type for e in defect_events] == ["probe_defect"]
    assert [e.event_type for e in change_events] == ["probe_change"]
