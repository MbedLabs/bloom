"""Reader visibility, mailbox authentication and report-request decisions."""

import asyncio
import base64
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api import attachments, documents, projects, report_requests, users
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.core.service_auth import create_service_credential
from app.models import (
    Project,
    Requirement,
    TestCampaign,
    TestCase,
    TestRunLink,
    TestSuite,
    TestSuiteItem,
    User,
)
from app.models.audit import AuditEvent
from app.models.user import UserRole
from tests.access_fixtures import project_access_fixture


@pytest.fixture
def requests_client(monkeypatch, tmp_path):
    """Real bearer guards and isolated source/run relationships."""
    monkeypatch.setattr(
        settings, "SERVICE_TOKEN_PEPPER", "test-report-request-pepper-32-characters"
    )
    from app.services import attachment_storage

    monkeypatch.setattr(attachment_storage, "get_attachment_root", lambda: tmp_path)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def seed():
        async with engine.begin() as connection:
            await connection.execute(text("PRAGMA foreign_keys=ON"))
            await connection.run_sync(Base.metadata.create_all)
        async with maker() as db:
            people = [
                User(
                    email=f"reader-{i}@example.com",
                    full_name=f"Reader {i}",
                    role=role,
                    hashed_password="unused",
                )
                for i, role in enumerate([UserRole.admin, UserRole.maintainer, UserRole.maintainer])
            ]
            project = Project(name="Demo", prefix="PRJ")
            db.add_all([*people, project])
            await db.flush()
            db.add(
                project_access_fixture(
                    user_id=people[1].id,
                    project_id=project.id,
                    permissions={
                        "TC": ["view"],
                        "TS": ["view"],
                        "REQ": ["view"],
                        "CMP": ["view"],
                        "RPT": ["view"],
                    },
                )
            )
            case = TestCase(
                project_id=project.id,
                tc_id="PRJ-TC-001",
                title="Check",
                last_bud_run_id=41,
                last_executed_at=datetime.utcnow(),
            )
            suite = TestSuite(project_id=project.id, suite_id="PRJ-TS-001", name="Suite")
            requirement = Requirement(
                project_id=project.id, req_id="PRJ-REQ-001", title="Requirement"
            )
            campaign = TestCampaign(
                project_id=project.id, campaign_id="PRJ-CMP-001", name="Campaign", bud_run_id=41
            )
            db.add_all([case, suite, requirement, campaign])
            await db.flush()
            db.add(TestSuiteItem(suite_id=suite.id, test_case_id=case.id, order=0))
            db.add(TestRunLink(requirement_id=requirement.id, test_run_id=41))
            await db.commit()
            _, token = await create_service_credential(
                db, created_by_user_id=people[0].id, name="Bud"
            )
            headers = [
                {
                    "Authorization": "Bearer "
                    + create_access_token({"sub": str(user.id), "type": "user", "ver": 1})
                }
                for user in people
            ]
            return (
                headers,
                {"Authorization": f"Bearer {token}"},
                [case.id, suite.id, requirement.id, campaign.id],
                project.id,
            )

    async def database():
        async with maker() as db:
            yield db
            await db.commit()

    seeded = asyncio.run(seed())
    app = FastAPI()
    app.include_router(report_requests.router, prefix="/api")
    app.include_router(attachments.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(projects.router, prefix="/api/projects")
    app.include_router(users.router, prefix="/api/users")
    app.dependency_overrides[get_db] = database
    with TestClient(app) as client:
        yield client, maker, *seeded
    asyncio.run(engine.dispose())


@pytest.mark.parametrize(
    "kind,index", [("test-case", 0), ("test-suite", 1), ("requirement", 2), ("campaign", 3)]
)
def test_visible_link_is_required_and_repeated_pending_is_one_request(requests_client, kind, index):
    client, _, (admin, reader, outsider), machine, ids, _ = requests_client
    body = {"source_kind": kind, "source_id": ids[index], "run_id": 41}
    assert client.post("/api/report-requests", json=body).status_code == 401
    assert client.post("/api/report-requests", json=body, headers=outsider).status_code == 404
    assert (
        client.post("/api/report-requests", json={**body, "run_id": 42}, headers=reader).status_code
        == 404
    )
    first = client.post("/api/report-requests", json=body, headers=reader)
    assert first.status_code == 201, first.text
    again = client.post("/api/report-requests", json=body, headers=reader)
    assert first.json()["id"] == again.json()["id"]
    assert client.get("/api/report-requests", params=body, headers=admin).json() is None
    assert client.get("/api/bud/report-requests", headers=reader).status_code == 401
    mailbox = client.get("/api/bud/report-requests", headers=machine).json()
    assert len(mailbox) == 1
    assert mailbox[0]["requester_email"] == "reader-1@example.com"


def test_refusal_reason_and_machine_attribution_reach_reader(requests_client):
    client, maker, (_, reader, _), machine, ids, _ = requests_client
    body = {"source_kind": "test-case", "source_id": ids[0], "run_id": 41}
    row = client.post("/api/report-requests", json=body, headers=reader).json()
    path = f"/api/bud/report-requests/{row['id']}/refuse"
    assert (
        client.post(
            path, headers=machine, json={"reason": " ", "publisher": "Publisher"}
        ).status_code
        == 422
    )
    response = client.post(
        path,
        headers=machine,
        json={"reason": "Evidence incomplete", "publisher": "Publisher (Bud user #7)"},
    )
    assert response.status_code == 200
    state = client.get("/api/report-requests", params=body, headers=reader).json()
    assert state["status"] == "refused"
    assert state["reason"] == "Evidence incomplete"
    assert "publisher" not in state

    async def audit():
        async with maker() as db:
            return (
                await db.scalars(select(AuditEvent).where(AuditEvent.action == "report.refused"))
            ).one()

    event = asyncio.run(audit())
    assert event.actor_type == "service"
    assert event.details["bud_publisher"] == "Publisher (Bud user #7)"


def test_only_successful_matching_report_delivery_closes_requests(requests_client):
    client, _, (_, reader, _), machine, ids, _ = requests_client
    body = {"source_kind": "test-case", "source_id": ids[0], "run_id": 41}
    row = client.post("/api/report-requests", json=body, headers=reader).json()
    payload = {
        "project_prefix": "PRJ",
        "bud_run_id": 41,
        "run_name": "Run",
        "files": [
            {
                "filename": "report.pdf",
                "content_type": "application/pdf",
                "content_base64": "invalid",
            }
        ],
    }
    assert client.post("/api/bud/test-reports", headers=machine, json=payload).status_code == 422
    assert (
        client.get("/api/report-requests", params=body, headers=reader).json()["status"]
        == "pending"
    )
    payload["files"][0]["content_base64"] = base64.b64encode(b"%PDF-1.4 report").decode()
    other = client.post(
        "/api/bud/test-reports", headers=machine, json={**payload, "bud_run_id": 42}
    )
    assert other.status_code == 201, other.text
    assert (
        client.get("/api/report-requests", params=body, headers=reader).json()["status"]
        == "pending"
    )
    published = client.post("/api/bud/test-reports", headers=machine, json=payload)
    assert published.status_code == 201, published.text
    state = client.get("/api/report-requests", params=body, headers=reader).json()
    assert state["status"] == "delivered"
    assert state["doc_id"] == published.json()["doc_id"]
    assert (
        client.post(
            f"/api/bud/report-requests/{row['id']}/refuse",
            headers=machine,
            json={"reason": "Late refusal", "publisher": "Publisher"},
        ).status_code
        == 409
    )


@pytest.mark.parametrize("target", ["project", "account"])
def test_explicit_deletions_keep_working_with_pending_report_requests(requests_client, target):
    client, _, (admin, reader, _), machine, ids, project_id = requests_client
    body = {"source_kind": "test-case", "source_id": ids[0], "run_id": 41}
    assert client.post("/api/report-requests", headers=reader, json=body).status_code == 201
    path = f"/api/projects/{project_id}" if target == "project" else "/api/users/2"
    response = client.delete(path, headers=admin)
    assert response.status_code == 204, response.text
    assert client.get("/api/bud/report-requests", headers=machine).json() == []


def test_deleting_a_delivered_document_preserves_the_request_history(requests_client):
    client, maker, (admin, reader, _), _, ids, project_id = requests_client
    from app.models import Document, ReportRequest

    async def delivered():
        async with maker() as db:
            document = Document(
                project_id=project_id, doc_id="PRJ-RPT-001", title="Report", doc_type="RPT"
            )
            db.add(document)
            await db.flush()
            db.add(
                ReportRequest(
                    project_id=project_id,
                    bud_run_id=41,
                    requester_id=2,
                    status="delivered",
                    document_id=document.id,
                )
            )
            await db.commit()
            return document.id

    document_id = asyncio.run(delivered())
    response = client.delete(f"/api/documents/{document_id}", headers=admin)
    assert response.status_code == 204, response.text
    body = {"source_kind": "test-case", "source_id": ids[0], "run_id": 41}
    state = client.get("/api/report-requests", params=body, headers=reader).json()
    assert state["status"] == "delivered" and state["doc_id"] is None
