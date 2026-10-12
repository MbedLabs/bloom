"""Real HTTP handoffs bind review, approval and archived content to their actors."""

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models import (
    ArtefactLink,
    ChangeRequest,
    Defect,
    DesignItem,
    Document,
    Project,
    Requirement,
    RiskItem,
)
from app.models import TestCampaign as CampaignModel
from app.models import TestCase as CaseModel
from app.models import TestConcept
from app.models import TestSuite as SuiteModel
from app.models.user import User, UserRole
from app.models.workflow import ArtefactWorkflow

KINDS = (
    ("requirement", Requirement, {"req_id": "PRJ-REQ-001", "title": "Requirement"}),
    ("test-case", CaseModel, {"tc_id": "PRJ-TC-001", "title": "Test case"}),
    ("document", Document, {"doc_id": "PRJ-SPEC-001", "doc_type": "SPEC", "title": "Spec"}),
    ("document", Document, {"doc_id": "PRJ-PRT-001", "doc_type": "PRT", "title": "Protocol"}),
    ("design", DesignItem, {"design_id": "PRJ-DES-001", "title": "Design"}),
    ("test-concept", TestConcept, {"concept_id": "PRJ-CPT-001", "name": "Concept"}),
    ("test-suite", SuiteModel, {"suite_id": "PRJ-TS-001", "name": "Suite"}),
    ("change", ChangeRequest, {"change_id": "PRJ-CHG-001", "title": "Change"}),
)


UPDATE_ROUTES = {
    "requirement": "requirements",
    "test-case": "test-cases",
    "document": "documents",
    "design": "designs",
    "test-concept": "test-concepts",
    "test-suite": "test-suites",
    "change": "changes",
}


@pytest.mark.parametrize("status", ["Accepted", "Mitigated", "Closed", "Monitoring"])
async def test_risk_registry_preserves_operational_status_and_filters(workflow_http, status):
    db, client, _, _ = workflow_http
    risk = RiskItem(project_id=1, risk_id="PRJ-RSK-001", title="Risk", status=status)
    db.add_all(
        [
            risk,
            Requirement(project_id=1, req_id="PRJ-REQ-001", title="Requirement", status="Draft"),
        ]
    )
    await db.flush()
    response = await client.get("/api/projects/PRJ/docs", params={"type": "RSK", "status": status})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert [(item["doc_id"], item["status"]) for item in response.json()["items"]] == [
        ("PRJ-RSK-001", status)
    ]
    detail = await client.get("/api/projects/PRJ/docs/risks/PRJ-RSK-001")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == status
    assert risk.status == status
    assert await db.scalar(select(ArtefactWorkflow)) is None


@pytest.mark.parametrize("status", ["Implemented", "Verified", "Active"])
async def test_unsupported_requirement_read_does_not_invent_draft(workflow_http, status):
    db, client, _, _ = workflow_http
    row = Requirement(
        project_id=1,
        req_id="PRJ-REQ-001",
        title="Preserved content",
        status=status,
        created_by_id=1,
    )
    db.add(row)
    await db.flush()
    path = f"/api/artefacts/requirement/{row.id}"
    response = await client.get(path + "/workflow")
    assert response.status_code == 200, response.text
    assert response.json()["phase"] is None
    assert response.json()["revision_number"] is None
    assert await db.scalar(select(ArtefactWorkflow)) is None
    registry = await client.get("/api/projects/PRJ/docs")
    assert registry.status_code == 200, registry.text
    assert registry.json()["items"][0]["status"] is None
    draft = await client.get("/api/projects/PRJ/docs", params={"status": "Draft"})
    assert draft.json()["total"] == 0
    assert row.status == status and row.title == "Preserved content"
    response = await client.post(path + "/draft")
    assert response.status_code == 200, response.text
    assert row.status == "Draft"
    assert row.title == "Preserved content"
    response = await client.get(path + "/workflow")
    assert response.json()["phase"] == "Draft"
    assert response.json()["revision_number"] == 1


@pytest.mark.parametrize("status", ["Submitted", "Closed"])
async def test_legacy_change_status_remains_visible_and_filterable(workflow_http, status):
    db, client, _, _ = workflow_http
    row = ChangeRequest(
        project_id=1,
        change_id="PRJ-CHG-001",
        title="Legacy change",
        status=status,
    )
    db.add(row)
    await db.flush()
    response = await client.get("/api/projects/PRJ/docs", params={"type": "CHG", "status": status})
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["status"] == status
    response = await client.get(f"/api/artefacts/change/{row.id}/workflow")
    assert response.status_code == 200, response.text
    assert response.json()["phase"] is None
    assert response.json()["revision_number"] is None
    assert row.status == status
    assert await db.scalar(select(ArtefactWorkflow)) is None


@pytest_asyncio.fixture
async def workflow_http(monkeypatch):
    """Exercise the actual application routes in an isolated transactional database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _record):
        """Enforce references while exercising real deletion and retention routes."""
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    deliveries = []
    monkeypatch.setattr("app.api.workflow.send_email", lambda **message: deliveries.append(message))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        db.info["workflow_deliveries"] = deliveries
        db.add(Project(id=1, name="Workflow", prefix="PRJ"))
        users = [
            User(
                id=i,
                email=f"person{i}@example.com",
                full_name=f"Person {i}",
                hashed_password="x",
                role=UserRole.admin,
                is_active=True,
            )
            for i in range(1, 5)
        ]
        db.add_all(users)
        await db.flush()
        current = [users[0]]

        async def session():
            yield db
            await db.flush()

        async def actor():
            return current[0]

        app.dependency_overrides[get_db] = session
        app.dependency_overrides[get_current_user] = actor
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield db, client, current, users
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)
            await db.rollback()
    await engine.dispose()


@pytest.mark.parametrize("slug,model,fields", KINDS)
async def test_controlled_type_has_creator_bound_workflow(workflow_http, slug, model, fields):
    db, client, _, _ = workflow_http
    row = model(project_id=1, created_by_id=1, status="Draft", **fields)
    db.add(row)
    await db.flush()
    response = await client.get(f"/api/artefacts/{slug}/{row.id}/workflow")
    assert response.status_code == 200, response.text
    assert response.json()["controlled"] is True
    assert response.json()["creator"]["id"] == 1
    assert response.json()["phase"] == "Draft"
    assert response.json()["actions"]["comment"] is False


async def test_reading_admin_cannot_comment_without_assignment(workflow_http):
    db, client, current, users = workflow_http
    row = Requirement(project_id=1, req_id="PRJ-REQ-001", title="Content", reviewer_id=2)
    db.add(row)
    await db.flush()
    current[0] = users[3]
    response = await client.post(
        f"/api/artefacts/requirement/{row.id}/comments", json={"body": "Read is not review"}
    )
    assert response.status_code == 403, response.text
    current[0] = users[1]
    response = await client.post(
        f"/api/artefacts/requirement/{row.id}/comments", json={"body": "Assigned reviewer"}
    )
    assert response.status_code == 201, response.text
    assert response.json()["author_user_id"] == 2


@pytest.mark.parametrize(
    "route,payload",
    [
        ("/api/requirements", {"title": "Requirement"}),
        ("/api/test-cases", {"title": "Case"}),
        ("/api/designs", {"title": "Design"}),
        ("/api/test-concepts", {"name": "Concept"}),
        ("/api/changes", {"title": "Change"}),
        ("/api/test-suites", {"name": "Suite"}),
    ],
)
async def test_api_creation_cannot_skip_draft(workflow_http, route, payload):
    _, client, _, _ = workflow_http
    response = await client.post(route, json={"project_id": 1, "status": "Approved", **payload})
    assert response.status_code == 422, response.text


async def test_direct_signed_approval_cannot_bypass_request(workflow_http):
    db, client, current, users = workflow_http
    row = Requirement(
        project_id=1,
        req_id="PRJ-REQ-001",
        title="Content",
        created_by_id=1,
        reviewer_id=2,
        approver_id=3,
    )
    db.add(row)
    await db.flush()
    current[0] = users[2]
    response = await client.post(
        f"/api/artefacts/requirement/{row.id}/sign-off", json={"step": "approve"}
    )
    assert response.status_code == 409, response.text
    assert row.status == "Draft"
    assert row.approved_by_id is None


@pytest.mark.parametrize("slug,model,fields", KINDS)
async def test_actual_review_approval_and_revision_preserve_content(
    workflow_http, slug, model, fields
):
    db, client, current, users = workflow_http
    row = model(project_id=1, created_by_id=1, status="Draft", **fields)
    db.add(row)
    await db.flush()
    path = f"/api/artefacts/{slug}/{row.id}"
    response = await client.put(
        path + "/workflow/assignees", json={"reviewer_id": 2, "approver_id": 3}
    )
    assert response.status_code == 200, response.text
    current[0] = users[1]
    response = await client.post(path + "/comments", json={"body": "Comment before review request"})
    assert response.status_code == 201, response.text
    current[0] = users[0]
    response = await client.post(path + "/requests", json={"kind": "review"})
    assert response.status_code == 201, response.text
    assert row.status == "Review"
    repeat = await client.post(path + "/requests", json={"kind": "review"})
    assert repeat.status_code == 200 and repeat.json()["already_requested"] is True
    requested_activity = await client.get(path + "/activity")
    assert requested_activity.status_code == 200, requested_activity.text
    requested_events = [event["event_type"] for event in requested_activity.json()]
    assert requested_events.count("review_requested") == 1
    assert not {"reviewed", "approved"} & set(requested_events)
    current[0] = users[1]
    response = await client.post(path + "/requests", json={"kind": "approval"})
    assert response.status_code == 409, response.text
    response = await client.post(
        path + "/comments", json={"body": "Reviewed the requested content"}
    )
    assert response.status_code == 201, response.text
    response = await client.post(path + "/requests", json={"kind": "approval"})
    assert response.status_code == 201, response.text
    registry = await client.get("/api/projects/PRJ/docs", params={"status": "Approval"})
    assert registry.status_code == 200, registry.text
    assert [(item["id"], item["status"]) for item in registry.json()["items"]] == [
        (row.id, "Approval")
    ]
    if slug == "requirement":
        detail = await client.get(f"/api/projects/PRJ/docs/requirements/{row.req_id}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["status"] == "Approval"
    current[0] = users[3]
    response = await client.post(path + "/sign-off", json={"step": "approve"})
    assert response.status_code == 403, response.text
    current[0] = users[2]
    response = await client.post(path + "/sign-off", json={"step": "approve"})
    assert response.status_code == 200, response.text
    assert row.status == "Approved"
    assert response.json()["reviewed_by_id"] == 2
    assert response.json()["approved_by_id"] == 3
    activity = await client.get(path + "/activity")
    assert activity.status_code == 200, activity.text
    signoffs = [
        event for event in activity.json() if event["event_type"] in {"reviewed", "approved"}
    ]
    assert sorted((event["event_type"], event["actor_user_id"]) for event in signoffs) == [
        ("approved", 3),
        ("reviewed", 2),
    ]
    assert all(event["created_at"] for event in signoffs)
    archive = await client.get(path + "/revisions/1")
    assert archive.status_code == 200, archive.text
    title = "title" if "title" in fields else "name"
    assert archive.json()["snapshot"]["fields"][title] == fields[title]
    change = ChangeRequest(
        project_id=1,
        created_by_id=1,
        change_id="PRJ-CHG-900",
        title="Authorized change",
        status="Approved",
    )
    db.add(change)
    await db.flush()
    current[0] = users[0]
    from app.services.document_workflow import artefact_identity

    code = artefact_identity(row)[1]
    if slug != "change":
        link = await client.post(
            "/api/links",
            json={
                "project_id": 1,
                "source_type": "CHG",
                "source_id": change.id,
                "target_type": code,
                "target_id": row.id,
                "role": "impacts",
            },
        )
        assert link.status_code == 201, link.text
        unchanged = await client.get(path + "/workflow")
        assert unchanged.json()["revision_number"] == 1
        assert unchanged.json()["actions"]["edit_current"] is True
    response = await client.patch(
        f"/api/{UPDATE_ROUTES[slug]}/{row.id}", json={title: "Saved changed content"}
    )
    if slug == "change":
        assert response.status_code == 409, response.text
        assert row.status == "Approved"
    else:
        assert response.status_code == 200, response.text
        assert row.status == "Draft"
        state = (await client.get(path + "/workflow")).json()
        assert state["revision_number"] == 2
        assert state["authorizing_change"]["id"] == change.id
        if slug == "document":
            assert row.version == "2"
        assert state["reviewed_by"] is None
        assert state["approved_by"] is None
        retained = await client.get(path + "/revisions/1")
        assert retained.json() == archive.json()


async def test_edit_during_review_supersedes_instead_of_answering(workflow_http):
    from app.models import ArtefactRequest

    db, client, current, users = workflow_http
    row = Requirement(
        project_id=1,
        req_id="PRJ-REQ-001",
        title="Original",
        created_by_id=1,
        reviewer_id=2,
        approver_id=3,
    )
    db.add(row)
    await db.flush()
    path = f"/api/artefacts/requirement/{row.id}"
    response = await client.post(path + "/requests", json={"kind": "review"})
    assert response.status_code == 201, response.text
    current[0] = users[1]
    await client.post(path + "/comments", json={"body": "Old content"})
    current[0] = users[0]
    response = await client.patch(f"/api/requirements/{row.id}", json={"title": "Changed"})
    assert response.status_code == 200, response.text
    assert row.status == "Draft"
    requests = (await db.execute(select(ArtefactRequest))).scalars().all()
    assert requests[0].status == "superseded"
    assert requests[0].decided_by_id == 1
    current[0] = users[1]
    response = await client.post(path + "/requests", json={"kind": "approval"})
    assert response.status_code == 409, response.text


async def test_unassigned_review_notifies_without_granting_comment_assignment(workflow_http):
    from app.models import ArtefactRequestRecipient

    db, client, current, users = workflow_http
    row = Requirement(project_id=1, req_id="PRJ-REQ-001", title="Content", created_by_id=1)
    db.add(row)
    await db.flush()
    path = f"/api/artefacts/requirement/{row.id}"
    state = await client.get(path + "/workflow")
    assert state.json()["actions"]["request_review"] is True
    request = await client.post(path + "/requests", json={"kind": "review"})
    assert request.status_code == 201, request.text
    recipients = (await db.scalars(select(ArtefactRequestRecipient.user_id))).all()
    assert set(recipients) == {1, 2, 3, 4}
    current[0] = users[1]
    state = await client.get(path + "/workflow")
    assert state.json()["actions"]["decline"] is True
    assert state.json()["actions"]["comment"] is False
    refused = await client.post(path + "/comments", json={"body": "Unassigned recipient"})
    assert refused.status_code == 403
    current[0] = users[0]
    assigned = await client.put(path + "/workflow/assignees", json={"reviewer_id": 2})
    assert assigned.status_code == 200, assigned.text
    current[0] = users[1]
    comment = await client.post(path + "/comments", json={"body": "Assigned review"})
    assert comment.status_code == 201, comment.text


async def test_ineligible_assignee_falls_back_to_visible_recipients(workflow_http):
    from app.models import ArtefactRequestRecipient

    db, client, current, users = workflow_http
    users[1].is_active = False
    row = Requirement(
        project_id=1, req_id="PRJ-REQ-001", title="Content", created_by_id=1, reviewer_id=2
    )
    db.add(row)
    await db.flush()
    path = f"/api/artefacts/requirement/{row.id}"
    request = await client.post(path + "/requests", json={"kind": "review"})
    assert request.status_code == 201, request.text
    recipients = (await db.scalars(select(ArtefactRequestRecipient.user_id))).all()
    assert set(recipients) == {1, 3, 4}
    current[0] = users[2]
    state = await client.get(path + "/workflow")
    assert state.json()["actions"]["decline"] is True
    declined = await client.post(f"/api/artefact-requests/{request.json()['id']}/decline")
    assert declined.status_code == 200, declined.text
    assert row.status == "Draft"


async def test_ineligible_approver_fallback_can_answer_delivered_request(workflow_http):
    db, client, current, users = workflow_http
    users[2].is_active = False
    row = Requirement(
        project_id=1,
        req_id="PRJ-REQ-001",
        title="Content",
        created_by_id=1,
        reviewer_id=2,
        approver_id=3,
    )
    db.add(row)
    await db.flush()
    path = f"/api/artefacts/requirement/{row.id}"
    request = await client.post(path + "/requests", json={"kind": "review"})
    assert request.status_code == 201, request.text
    current[0] = users[1]
    comment = await client.post(path + "/comments", json={"body": "Assigned review"})
    assert comment.status_code == 201, comment.text
    approval = await client.post(path + "/requests", json={"kind": "approval"})
    assert approval.status_code == 201, approval.text
    current[0] = users[3]
    state = await client.get(path + "/workflow")
    assert state.json()["actions"]["approve"] is True
    approved = await client.post(path + "/sign-off", json={"step": "approve"})
    assert approved.status_code == 200, approved.text
    assert row.approved_by_id == 4


async def test_external_assigned_customer_reviewer_has_no_implicit_read(workflow_http):
    from app.core.security import _access_map
    from tests.access_fixtures import project_access_fixture

    db, client, current, users = workflow_http
    users[3].role = UserRole.external
    row = Requirement(
        project_id=1,
        req_id="PRJ-REQ-001",
        title="Customer document",
        visibility="customer",
        created_by_id=1,
        reviewer_id=4,
    )
    internal = Requirement(
        project_id=1,
        req_id="PRJ-REQ-002",
        title="Internal document",
        visibility="internal",
        created_by_id=1,
        reviewer_id=4,
    )
    entry = project_access_fixture(
        user_id=4, project_id=1, permissions={"REQ": ["review"]}, visibility="customer"
    )
    db.add_all([row, internal, entry])
    await db.flush()
    current[0] = users[3]
    users[3].access_map = await _access_map(db, users[3])
    path = f"/api/artefacts/requirement/{row.id}"
    response = await client.get(path + "/workflow")
    assert response.status_code == 404, response.text
    entry.policies[0].permissions = {"REQ": ["view", "review"]}
    await db.flush()
    users[3].access_map = await _access_map(db, users[3])
    response = await client.get(path + "/workflow")
    assert response.status_code == 200, response.text
    assert response.json()["actions"]["comment"] is True
    response = await client.post(path + "/comments", json={"body": "Customer review"})
    assert response.status_code == 201, response.text
    response = await client.post(
        f"/api/artefacts/requirement/{internal.id}/comments", json={"body": "Hidden"}
    )
    assert response.status_code == 404, response.text
    entry.policies[0].permissions = {"REQ": ["view"]}
    await db.flush()
    users[3].access_map = await _access_map(db, users[3])
    response = await client.post(path + "/comments", json={"body": "Review revoked"})
    assert response.status_code == 403, response.text


async def test_project_deletion_retains_approved_workflow_history(workflow_http):
    from app.models import ArtefactRevision, ArtefactWorkflow

    db, client, current, users = workflow_http
    row = Requirement(
        project_id=1,
        req_id="PRJ-REQ-001",
        title="Preserved",
        created_by_id=1,
        reviewer_id=2,
        approver_id=3,
    )
    db.add(row)
    await db.flush()
    path = f"/api/artefacts/requirement/{row.id}"
    review = await client.post(path + "/requests", json={"kind": "review"})
    assert review.status_code == 201, review.text
    current[0] = users[1]
    comment = await client.post(path + "/comments", json={"body": "Reviewed content"})
    assert comment.status_code == 201, comment.text
    approval = await client.post(path + "/requests", json={"kind": "approval"})
    assert approval.status_code == 201, approval.text
    current[0] = users[2]
    approved = await client.post(path + "/sign-off", json={"step": "approve"})
    assert approved.status_code == 200, approved.text
    revision = await db.scalar(select(ArtefactRevision))
    original = revision.content_snapshot
    state = await db.scalar(select(ArtefactWorkflow))
    current[0] = users[0]
    removed = await client.delete("/api/projects/1")
    assert removed.status_code == 204, removed.text
    await db.refresh(state)
    await db.refresh(revision)
    assert state.project_id is None
    assert revision.content_snapshot == original
    assert (await client.get(path + "/revisions/1")).status_code == 404


async def test_external_owner_needs_selected_review_policy_and_assignment(workflow_http):
    from app.core.security import _access_map
    from tests.access_fixtures import project_access_fixture

    db, client, current, users = workflow_http
    users[3].role = UserRole.external
    row = Requirement(
        project_id=1,
        req_id="PRJ-REQ-001",
        title="Customer review",
        visibility="customer",
        created_by_id=1,
        reviewer_id=4,
    )
    entry = project_access_fixture(
        user_id=4, project_id=1, permissions={"REQ": ["view"]}, visibility="customer"
    )
    entry.owner = True
    db.add_all([row, entry])
    await db.flush()
    current[0] = users[3]
    users[3].access_map = await _access_map(db, users[3])
    path = f"/api/artefacts/requirement/{row.id}"
    denied = await client.post(path + "/comments", json={"body": "No Review policy"})
    assert denied.status_code == 403, denied.text
    entry.policies[0].permissions = {"REQ": ["view", "review"]}
    await db.flush()
    users[3].access_map = await _access_map(db, users[3])
    allowed = await client.post(path + "/comments", json={"body": "Policy granted and assigned"})
    assert allowed.status_code == 201, allowed.text
    row.reviewer_id = 2
    await db.flush()
    unassigned = await client.post(path + "/comments", json={"body": "Not assigned"})
    assert unassigned.status_code == 403, unassigned.text


@pytest.mark.parametrize(
    "route,payload",
    [
        ("/api/requirements", {"title": "Requirement"}),
        ("/api/test-cases", {"title": "Case"}),
        ("/api/designs", {"title": "Design"}),
        ("/api/test-concepts", {"name": "Concept"}),
        ("/api/changes", {"title": "Change"}),
        ("/api/test-suites", {"name": "Suite"}),
        ("/api/projects/1/documents", {"title": "Specification", "doc_type": "SPEC"}),
        ("/api/projects/1/documents", {"title": "Protocol", "doc_type": "PRT"}),
    ],
)
async def test_real_controlled_creation_is_draft_and_creator_owned(workflow_http, route, payload):
    _, client, _, _ = workflow_http
    response = await client.post(route, json={"project_id": 1, **payload})
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "Draft"
    slug = {
        "/api/requirements": "requirement",
        "/api/test-cases": "test-case",
        "/api/designs": "design",
        "/api/test-concepts": "test-concept",
        "/api/changes": "change",
        "/api/test-suites": "test-suite",
        "/api/projects/1/documents": "document",
    }[route]
    workflow = await client.get(f"/api/artefacts/{slug}/{response.json()['id']}/workflow")
    assert workflow.status_code == 200, workflow.text
    assert workflow.json()["creator"]["id"] == 1


async def test_project_notification_dependency_is_scoped_to_deleted_project(workflow_http):
    from app.models import Notification

    db, client, current, users = workflow_http
    db.add(Project(id=2, name="Retained", prefix="RET"))
    await db.flush()
    removed = Notification(
        user_id=1, project_id=1, event_type="review", title="Pending project review"
    )
    retained = Notification(user_id=1, event_type="account", title="Account notification")
    other = Notification(user_id=1, project_id=2, event_type="review", title="Other project review")
    db.add_all([removed, retained, other])
    await db.flush()
    users[3].role = UserRole.maintainer
    current[0] = users[3]
    refused = await client.delete("/api/projects/1")
    assert refused.status_code == 403, refused.text
    assert (await db.scalars(select(Notification.id).order_by(Notification.id))).all() == [
        removed.id,
        retained.id,
        other.id,
    ]
    current[0] = users[0]
    response = await client.delete("/api/projects/1")
    assert response.status_code == 204, response.text
    assert (await db.scalars(select(Notification.id).order_by(Notification.id))).all() == [
        retained.id,
        other.id,
    ]


async def test_requester_deletion_removes_requests_but_preserves_approved_identity(workflow_http):
    from app.models import ArtefactComment, ArtefactRequest, ArtefactRevision

    db, client, current, users = workflow_http
    row = Requirement(
        project_id=1,
        req_id="PRJ-REQ-001",
        title="Approved content",
        created_by_id=1,
        reviewer_id=2,
        approver_id=3,
    )
    db.add(row)
    await db.flush()
    path = f"/api/artefacts/requirement/{row.id}"
    review = await client.post(path + "/requests", json={"kind": "review"})
    assert review.status_code == 201, review.text
    current[0] = users[1]
    comment = await client.post(path + "/comments", json={"body": "Reviewed"})
    assert comment.status_code == 201, comment.text
    approval = await client.post(path + "/requests", json={"kind": "approval"})
    assert approval.status_code == 201, approval.text
    current[0] = users[2]
    approved = await client.post(path + "/sign-off", json={"step": "approve"})
    assert approved.status_code == 200, approved.text
    revision = await db.scalar(select(ArtefactRevision))
    snapshot = revision.content_snapshot
    current[0] = users[3]
    deleted = await client.delete("/api/users/1")
    assert deleted.status_code == 204, deleted.text
    db.expire_all()
    requests = (await db.scalars(select(ArtefactRequest))).all()
    assert [request.id for request in requests] == [approval.json()["id"]]
    retained = await db.scalar(select(ArtefactRevision))
    assert retained.content_snapshot == snapshot
    assert retained.reviewed_by_id == 2
    assert retained.approved_by_id == 3
    assert retained.content_snapshot["signoff_identities"]["2"]["full_name"] == "Person 2"
    assert retained.content_snapshot["signoff_identities"]["3"]["full_name"] == "Person 3"
    retained_comment = await db.get(ArtefactComment, comment.json()["id"])
    assert retained_comment.review_request_id is None


async def test_project_pending_requests_filter_origin_membership_and_current_review(workflow_http):
    from app.core.security import _access_map
    from tests.access_fixtures import project_access_fixture

    db, client, current, users = workflow_http
    users[3].role = UserRole.external
    entry = project_access_fixture(
        user_id=4, project_id=1, permissions={"REQ": ["view", "review"]}, visibility="customer"
    )
    customer = Requirement(
        project_id=1,
        req_id="PRJ-REQ-001",
        title="Visible request",
        visibility="customer",
        created_by_id=1,
        reviewer_id=4,
    )
    internal = Requirement(
        project_id=1,
        req_id="PRJ-REQ-002",
        title="Hidden request",
        visibility="internal",
        created_by_id=1,
        reviewer_id=2,
    )
    db.add_all([entry, customer, internal, Project(id=2, name="Other", prefix="OTH")])
    await db.flush()
    for row in (customer, internal):
        request = await client.post(
            f"/api/artefacts/requirement/{row.id}/requests", json={"kind": "review"}
        )
        assert request.status_code == 201, request.text
    current[0] = users[3]
    users[3].access_map = await _access_map(db, users[3])
    visible = await client.get("/api/projects/1/artefact-requests")
    assert visible.status_code == 200, visible.text
    assert [(item["public_id"], item["doc_type"]) for item in visible.json()] == [
        ("PRJ-REQ-001", "REQ")
    ]
    assert (await client.get("/api/projects/2/artefact-requests")).status_code == 403
    entry.policies[0].permissions = {"REQ": ["view"]}
    await db.flush()
    users[3].access_map = await _access_map(db, users[3])
    revoked = await client.get("/api/projects/1/artefact-requests")
    assert revoked.status_code == 200 and revoked.json() == []


async def test_request_delivery_repeat_suppression_decline_and_actual_audit_actor(workflow_http):
    from app.models import ArtefactRequest, Notification
    from app.models.audit import AuditEvent

    db, client, current, users = workflow_http
    row = Requirement(
        project_id=1, req_id="PRJ-REQ-001", title="Review delivery", created_by_id=1, reviewer_id=2
    )
    db.add(row)
    await db.flush()
    path = f"/api/artefacts/requirement/{row.id}/requests"
    first = await client.post(path, json={"kind": "review"})
    assert first.status_code == 201, first.text
    assert [message["to_email"] for message in db.info["workflow_deliveries"]] == [users[1].email]
    repeat = await client.post(path, json={"kind": "review"})
    assert repeat.status_code == 200 and repeat.json()["already_requested"] is True
    assert len(db.info["workflow_deliveries"]) == 1
    assert len((await db.scalars(select(Notification))).all()) == 1
    current[0] = users[1]
    declined = await client.post(f"/api/artefact-requests/{first.json()['id']}/decline")
    assert declined.status_code == 200, declined.text
    assert [message["to_email"] for message in db.info["workflow_deliveries"]] == [
        users[1].email,
        users[0].email,
    ]
    request = await db.get(ArtefactRequest, first.json()["id"])
    assert request.status == "declined" and request.decided_by_id == 2
    assert request.decided_at is not None
    events = (
        await db.scalars(
            select(AuditEvent).where(AuditEvent.action.like("workflow.%")).order_by(AuditEvent.id)
        )
    ).all()
    assert [(event.action, event.actor_user_id) for event in events] == [
        ("workflow.requested", 1),
        ("workflow.declined", 2),
    ]


@pytest.mark.parametrize(
    "slug,model,fields",
    [
        ("document", Document, {"doc_id": "PRJ-RPT-001", "doc_type": "RPT", "title": "Report"}),
        ("document", Document, {"doc_id": "PRJ-STD-001", "doc_type": "STD", "title": "Standard"}),
        ("risk", RiskItem, {"risk_id": "PRJ-RSK-001", "title": "Risk"}),
        ("defect", Defect, {"defect_id": "PRJ-DEF-001", "title": "Defect"}),
        ("campaign", CampaignModel, {"campaign_id": "PRJ-CMP-001", "name": "Campaign"}),
    ],
)
async def test_operational_exceptions_keep_status_and_require_assigned_reviewer(
    workflow_http, slug, model, fields
):
    db, client, current, users = workflow_http
    row = model(project_id=1, created_by_id=1, **fields)
    db.add(row)
    await db.flush()
    status = row.status
    path = f"/api/artefacts/{slug}/{row.id}"
    denied = await client.post(path + "/comments", json={"body": "Not assigned"})
    assert denied.status_code == 403, denied.text
    assignment = await client.put(path + "/workflow/assignees", json={"reviewer_id": 2})
    assert assignment.status_code == 200, assignment.text
    current[0] = users[1]
    allowed = await client.post(path + "/comments", json={"body": "Assigned reviewer"})
    assert allowed.status_code == 201, allowed.text
    workflow = await client.get(path + "/workflow")
    assert workflow.status_code == 200, workflow.text
    assert workflow.json()["controlled"] is False
    assert workflow.json()["status"] == row.status == status
    assert workflow.json()["actions"]["request_review"] is False
    current[0] = users[2]
    denied = await client.post(path + "/comments", json={"body": "Unassigned admin"})
    assert denied.status_code == 403, denied.text


@pytest.mark.parametrize("slug,model,fields", KINDS[:-1])
async def test_approved_correction_reapproves_without_advancing_numbers(
    workflow_http, slug, model, fields
):
    db, client, current, users = workflow_http
    row = model(project_id=1, created_by_id=1, status="Approved", **fields)
    db.add(
        ChangeRequest(
            project_id=1,
            change_id="PRJ-CHG-UNLINKED",
            title="Unlinked approved change",
            status="Approved",
        )
    )
    db.add(row)
    await db.flush()
    title = "title" if "title" in fields else "name"
    path = f"/api/artefacts/{slug}/{row.id}"
    state = await client.get(path + "/workflow")
    assert state.json()["actions"]["edit_current"] is True
    original_version = getattr(row, "version", None)
    response = await client.patch(
        f"/api/{UPDATE_ROUTES[slug]}/{row.id}", json={title: fields[title]}
    )
    assert response.status_code == 200, response.text
    assert row.status == "Approved"
    response = await client.post(path + "/revisions", json={"change_request_id": 9999})
    assert response.status_code == 409
    current[0] = users[3]
    response = await client.patch(
        f"/api/{UPDATE_ROUTES[slug]}/{row.id}", json={title: "Corrected mistake"}
    )
    assert response.status_code == 200, response.text
    state = (await client.get(path + "/workflow")).json()
    assert state["phase"] == "Draft" and state["revision_number"] == 1
    assert state["creator"]["id"] == 4
    assert state["reviewed_by"] is state["approved_by"] is None
    assert getattr(row, "version", None) == original_version
    original = await client.get(path + "/revisions/1")
    assert original.json()["snapshot"]["fields"][title] == fields[title]
    response = await client.put(
        path + "/workflow/assignees", json={"reviewer_id": 2, "approver_id": 3}
    )
    assert response.status_code == 200, response.text
    response = await client.post(path + "/requests", json={"kind": "review"})
    assert response.status_code == 201, response.text
    current[0] = users[1]
    response = await client.post(path + "/comments", json={"body": "Checked correction"})
    assert response.status_code == 201, response.text
    response = await client.post(path + "/requests", json={"kind": "approval"})
    assert response.status_code == 201, response.text
    current[0] = users[2]
    response = await client.post(path + "/sign-off", json={"step": "approve"})
    assert response.status_code == 200, response.text
    state = (await client.get(path + "/workflow")).json()
    assert state["phase"] == "Approved" and state["revision_number"] == 1
    assert getattr(row, "version", None) == original_version
    assert (await client.get(path + "/revisions/1")).json() == original.json()


async def test_used_linked_change_does_not_bump_each_correction(workflow_http):
    db, client, current, users = workflow_http
    row = Document(
        project_id=1,
        doc_id="PRJ-SPEC-001",
        doc_type="SPEC",
        title="Approved",
        status="Approved",
        version="1.0",
        created_by_id=1,
    )
    change = ChangeRequest(
        project_id=1, change_id="PRJ-CHG-001", title="Authorized", status="Approved"
    )
    db.add_all([row, change])
    await db.flush()
    link = await client.post(
        "/api/links",
        json={
            "project_id": 1,
            "source_type": "CHG",
            "source_id": change.id,
            "target_type": "SPEC",
            "target_id": row.id,
            "role": "impacts",
        },
    )
    assert link.status_code == 201, link.text
    response = await client.patch(
        f"/api/documents/{row.id}",
        json={"title": "Changed", "status": "Approved", "version": "1.0"},
    )
    assert response.status_code == 200, response.text
    assert row.version == "2" and row.status == "Draft"
    response = await client.patch(f"/api/documents/{row.id}", json={"title": "Further correction"})
    assert response.status_code == 200, response.text
    state = (await client.get(f"/api/artefacts/document/{row.id}/workflow")).json()
    assert state["revision_number"] == 2 and row.version == "2"
    assert state["authorizing_change"]["id"] == change.id

    path = f"/api/artefacts/document/{row.id}"
    response = await client.put(
        path + "/workflow/assignees", json={"reviewer_id": 2, "approver_id": 3}
    )
    assert response.status_code == 200, response.text
    response = await client.post(path + "/requests", json={"kind": "review"})
    assert response.status_code == 201, response.text
    current[0] = users[1]
    response = await client.post(path + "/comments", json={"body": "Reviewed changed content"})
    assert response.status_code == 201, response.text
    response = await client.post(path + "/requests", json={"kind": "approval"})
    assert response.status_code == 201, response.text
    current[0] = users[2]
    response = await client.post(path + "/sign-off", json={"step": "approve"})
    assert response.status_code == 200, response.text
    retained = (await client.get(path + "/revisions/2")).json()
    current[0] = users[0]
    response = await client.patch(
        f"/api/documents/{row.id}", json={"title": "Corrected after approval"}
    )
    assert response.status_code == 200, response.text
    state = (await client.get(path + "/workflow")).json()
    assert state["phase"] == "Draft" and state["revision_number"] == 2
    assert row.version == "2"
    assert (await client.get(path + "/revisions/2")).json() == retained
    next_change = ChangeRequest(
        project_id=1, change_id="PRJ-CHG-002", title="Next change", status="Approved"
    )
    db.add(next_change)
    await db.flush()
    response = await client.post(
        "/api/links",
        json={
            "project_id": 1,
            "source_type": "CHG",
            "source_id": next_change.id,
            "target_type": "SPEC",
            "target_id": row.id,
            "role": "impacts",
        },
    )
    assert response.status_code == 201, response.text
    response = await client.patch(
        f"/api/documents/{row.id}", json={"title": "Next authorized change"}
    )
    assert response.status_code == 200, response.text
    state = (await client.get(path + "/workflow")).json()
    assert state["revision_number"] == 3 and row.version == "3"
    assert state["authorizing_change"]["id"] == next_change.id


async def test_linked_unapproved_change_cannot_authorize_saved_revision(workflow_http):
    db, client, _, _ = workflow_http
    row = Requirement(
        project_id=1, req_id="PRJ-REQ-001", title="Approved", status="Approved", created_by_id=1
    )
    change = ChangeRequest(project_id=1, change_id="PRJ-CHG-001", title="Pending", status="Draft")
    db.add_all([row, change])
    await db.flush()
    link = await client.post(
        "/api/links",
        json={
            "project_id": 1,
            "source_type": "CHG",
            "source_id": change.id,
            "target_type": "REQ",
            "target_id": row.id,
            "role": "impacts",
        },
    )
    assert link.status_code == 201, link.text
    response = await client.patch(
        f"/api/requirements/{row.id}", json={"title": "Unauthorized change"}
    )
    assert response.status_code == 409, response.text
    assert row.title == "Approved" and row.status == "Approved"
    state = (await client.get(f"/api/artefacts/requirement/{row.id}/workflow")).json()
    assert state["revision_number"] == 1
    assert state["revisions"] == []


async def test_controlled_version_cannot_be_changed_without_content_authorization(workflow_http):
    db, client, _, _ = workflow_http
    row = Document(
        project_id=1,
        doc_id="PRJ-SPEC-001",
        doc_type="SPEC",
        title="Approved",
        status="Approved",
        version="1",
        created_by_id=1,
    )
    db.add(row)
    await db.flush()
    response = await client.patch(f"/api/documents/{row.id}", json={"version": "4"})
    assert response.status_code == 409, response.text
    assert row.version == "1" and row.status == "Approved"
