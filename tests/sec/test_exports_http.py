"""Exports: the PDFs render, and every export holds only what the user may see."""

import asyncio
import csv
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models import ArtefactLink, AuditEvent, Project, Requirement, TestCase, User
from app.models.groups import Group, GroupMembership, GroupProjectGrant, Policy
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


def _project_with_artefacts(session_maker):
    """A project with one customer-visible and one internal requirement, each verified."""
    [project] = _add(session_maker, Project(name="Export project", prefix="EXP"))
    reqs = _add(
        session_maker,
        Requirement(
            project_id=project.id, req_id="EXP-REQ-001", title="Shown", visibility="customer"
        ),
        Requirement(
            project_id=project.id,
            req_id="EXP-REQ-002",
            title="Hidden requirement",
            visibility="internal",
        ),
    )
    tcs = _add(
        session_maker,
        TestCase(
            project_id=project.id,
            tc_id="EXP-TC-001",
            title="Shown test",
            visibility="customer",
            last_execution_status="Passed",
        ),
        TestCase(
            project_id=project.id, tc_id="EXP-TC-002", title="Hidden test", visibility="internal"
        ),
    )
    _add(
        session_maker,
        *[
            ArtefactLink(
                project_id=project.id,
                source_type="TC",
                source_id=tc.id,
                target_type="REQ",
                target_id=req.id,
                role="verifies",
            )
            for req, tc in zip(reqs, tcs)
        ],
    )
    return project


def _external_exporter(session_maker, project):
    """An external user whose group policy lets them view and export requirements and tests."""
    user = _user(session_maker, "reader@example.com", UserRole.external)
    [policy] = _add(
        session_maker,
        Policy(
            name="Exporting reader",
            base_role="external",
            permissions={"requirement": ["view", "export"], "test_case": ["view", "export"]},
        ),
    )
    [group] = _add(session_maker, Group(name="Readers", policy_id=policy.id))
    _add(
        session_maker,
        GroupMembership(group_id=group.id, user_id=user.id),
        GroupProjectGrant(group_id=group.id, project_id=project.id),
    )
    return user


def test_every_pdf_renders_on_the_letterhead(harness):
    client, session_maker = harness
    _user(session_maker, "boss@example.com", UserRole.admin)
    project = _project_with_artefacts(session_maker)
    headers = _login(client, "boss@example.com")

    for path in (
        f"/api/projects/{project.id}/export/requirements?format=pdf",
        f"/api/projects/{project.id}/export/traceability?format=pdf",
        f"/api/projects/{project.id}/export/test-cases?format=pdf",
        f"/api/projects/{project.id}/export/verification-dossier",
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 200, (path, response.text)
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")

    kinds = {event.details["kind"] for event in _events(session_maker, "export.generated")}
    assert kinds == {"requirements", "traceability", "test_cases", "verification_dossier"}


def test_an_external_exporter_gets_only_what_they_may_see(harness):
    client, session_maker = harness
    project = _project_with_artefacts(session_maker)
    _external_exporter(session_maker, project)
    headers = _login(client, "reader@example.com")

    requirements = client.get(f"/api/projects/{project.id}/export/requirements", headers=headers)
    matrix = client.get(f"/api/projects/{project.id}/export/traceability", headers=headers)
    tests = client.get(f"/api/projects/{project.id}/export/test-cases", headers=headers)

    assert requirements.status_code == 200, requirements.text
    assert [row["req_id"] for row in csv.DictReader(io.StringIO(requirements.text))] == [
        "EXP-REQ-001"
    ]
    matrix_rows = list(csv.DictReader(io.StringIO(matrix.text)))
    assert [(row["req_id"], row["tc_id"]) for row in matrix_rows] == [("EXP-REQ-001", "EXP-TC-001")]
    assert [row["tc_id"] for row in csv.DictReader(io.StringIO(tests.text))] == ["EXP-TC-001"]
    assert "Hidden" not in requirements.text + matrix.text + tests.text


def test_the_dossier_needs_test_case_export_too(harness):
    client, session_maker = harness
    project = _project_with_artefacts(session_maker)
    user = _user(session_maker, "author@example.com", UserRole.external)
    [policy] = _add(
        session_maker,
        Policy(
            name="Requirement exporter",
            base_role="external",
            permissions={"requirement": ["view", "export"]},
        ),
    )
    [group] = _add(session_maker, Group(name="Authors", policy_id=policy.id))
    _add(
        session_maker,
        GroupMembership(group_id=group.id, user_id=user.id),
        GroupProjectGrant(group_id=group.id, project_id=project.id),
    )
    headers = _login(client, "author@example.com")

    response = client.get(
        f"/api/projects/{project.id}/export/verification-dossier", headers=headers
    )

    assert response.status_code == 403
