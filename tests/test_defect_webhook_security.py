"""Regression tests: defect webhook signature enforcement (auth-bypass fix).

Previously both webhook handlers only verified the signature/token when the
header was present — so an attacker could spoof defect state changes simply by
omitting the header. With a webhook secret configured, verification is now
mandatory.
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
from app.models import Defect, DefectSyncEvent, IntegrationSetting, Project

SECRET = "hook-secret-123"


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
                external_tracker="github",
                external_repo_full_name="acme/widget",
                external_issue_number=42,
            )
        )
        setup.add(
            Defect(
                project_id=project.id,
                defect_id="ALP-DEF-002",
                title="GitLab defect",
                status="Open",
                external_tracker="gitlab",
                external_repo_full_name="acme/widget",
                external_issue_number=7,
            )
        )
        setup.add(
            IntegrationSetting(
                project_id=project.id, tracker="github", webhook_secret=SECRET, enabled=True
            )
        )
        setup.add(
            IntegrationSetting(
                project_id=project.id, tracker="gitlab", webhook_secret=SECRET, enabled=True
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


def _github_payload() -> bytes:
    return json.dumps(
        {
            "action": "closed",
            "issue": {"number": 42, "state": "closed"},
            "repository": {"full_name": "acme/widget"},
        }
    ).encode()


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


async def _defect_status(maker, defect_id: str) -> str:
    async with maker() as session:
        defect = (
            await session.execute(select(Defect).where(Defect.defect_id == defect_id))
        ).scalar_one()
        return defect.status


def test_github_webhook_rejects_missing_signature(env):
    client, maker = env
    body = _github_payload()
    response = client.post(
        "/api/integrations/github/webhook",
        content=body,
        headers={"X-GitHub-Event": "issues", "Content-Type": "application/json"},
    )
    assert response.status_code == 403  # bypass attempt rejected


def test_github_webhook_rejects_wrong_signature(env):
    client, maker = env
    body = _github_payload()
    response = client.post(
        "/api/integrations/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": "sha256=" + "0" * 64,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_github_webhook_accepts_valid_signature_and_syncs(env):
    client, maker = env
    body = _github_payload()
    response = client.post(
        "/api/integrations/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Delivery": "delivery-1",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert await _defect_status(maker, "ALP-DEF-001") == "Closed"

    # replayed delivery id is deduplicated
    replay = client.post(
        "/api/integrations/github/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Delivery": "delivery-1",
            "Content-Type": "application/json",
        },
    )
    assert replay.json()["status"] == "duplicate"


@pytest.mark.anyio
async def test_gitlab_webhook_rejects_missing_token(env):
    client, maker = env
    response = client.post(
        "/api/integrations/gitlab/webhook",
        json={
            "object_attributes": {"iid": 7, "state": "closed", "action": "close"},
            "project": {"path_with_namespace": "acme/widget"},
        },
        headers={"X-Gitlab-Event": "Issue Hook"},
    )
    assert response.status_code == 403
    assert await _defect_status(maker, "ALP-DEF-002") == "Open"  # unchanged


def test_gitlab_webhook_accepts_valid_token(env):
    client, maker = env
    response = client.post(
        "/api/integrations/gitlab/webhook",
        json={
            "object_attributes": {"iid": 7, "state": "closed", "action": "close"},
            "project": {"path_with_namespace": "acme/widget"},
        },
        headers={"X-Gitlab-Event": "Issue Hook", "X-Gitlab-Token": SECRET},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"


@pytest.mark.anyio
async def test_rejected_github_attempt_does_not_mutate_defect(env):
    client, maker = env
    body = _github_payload()
    response = client.post(
        "/api/integrations/github/webhook",
        content=body,
        headers={"X-GitHub-Event": "issues", "Content-Type": "application/json"},
    )
    assert response.status_code == 403
    assert await _defect_status(maker, "ALP-DEF-001") == "Open"  # spoof had no effect

    async with maker() as session:
        events = (await session.execute(select(DefectSyncEvent))).scalars().all()
        processed = [e for e in events if e.success]
        assert processed == []  # nothing recorded as successful
