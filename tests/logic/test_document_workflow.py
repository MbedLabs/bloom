"""Controlled workflow storage preserves approved content and rejects bypass writes."""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models import (
    ChangeRequest,
    DesignItem,
    Document,
    DocumentAttachment,
    DocumentSection,
    Project,
    Requirement,
    RiskItem,
)
from app.models import TestCase as Case
from app.models import TestConcept as Concept
from app.models import TestSuite as Suite
from app.models import TestSuiteItem as SuiteItem
from app.models import User, UserRole


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        db.add_all(
            [
                Project(name="Workflow", prefix="WFL"),
                User(
                    email="workflow@example.com",
                    full_name="Workflow Author",
                    hashed_password="x",
                    role=UserRole.admin,
                ),
            ]
        )
        await db.commit()
        yield db
    await engine.dispose()


def _row(kind, status="Approved"):
    """Create one controlled fixture document."""
    values = dict(project_id=1, status=status, created_by_id=1)
    if kind == "REQ":
        return Requirement(req_id="WFL-REQ-001", title="Original", **values)
    if kind == "TC":
        return Case(tc_id="WFL-TC-001", title="Original", **values)
    if kind in {"SPEC", "PRT"}:
        return Document(doc_id=f"WFL-{kind}-001", doc_type=kind, title="Original", **values)
    if kind == "DES":
        return DesignItem(design_id="WFL-DES-001", title="Original", **values)
    if kind == "CPT":
        return Concept(concept_id="WFL-CPT-001", name="Original", **values)
    if kind == "TS":
        return Suite(suite_id="WFL-TS-001", name="Original", **values)
    return ChangeRequest(change_id="WFL-CHG-001", title="Original", **values)


async def _saved(db, kind, status="Approved"):
    """Persist a fixture without fabricating a workflow history."""
    row = _row(kind, status)
    db.add(row)
    await db.commit()
    return row


@pytest.mark.parametrize("kind", ["REQ", "SPEC", "TC", "DES", "CPT", "PRT", "TS", "CHG"])
async def test_unguarded_approved_authored_write_is_refused(session, kind):
    row = await _saved(session, kind)
    setattr(row, "name" if kind in {"TS", "CPT"} else "title", "Overwritten")
    with pytest.raises(HTTPException) as refused:
        await session.flush()
    assert refused.value.status_code == 409


async def test_unguarded_direct_approval_transition_is_refused(session):
    row = await _saved(session, "REQ", "Draft")
    row.status = "Approved"
    with pytest.raises(HTTPException) as refused:
        await session.flush()
    assert refused.value.status_code == 409


async def test_change_default_is_draft(session):
    row = ChangeRequest(project_id=1, change_id="WFL-CHG-001", title="Draft proposal")
    session.add(row)
    await session.flush()
    assert row.status == "Draft"


@pytest.mark.parametrize("child", ["section", "attachment", "suite-item"])
async def test_unguarded_child_addition_to_approved_parent_is_refused(session, child):
    if child == "suite-item":
        parent = await _saved(session, "TS")
        case = await _saved(session, "TC", "Draft")
        session.add(SuiteItem(suite_id=parent.id, test_case_id=case.id))
    else:
        parent = await _saved(session, "SPEC")
        if child == "section":
            session.add(DocumentSection(document_id=parent.id, title="Unexpected"))
        else:
            session.add(
                DocumentAttachment(
                    document_id=parent.id,
                    filename="unexpected.txt",
                    original_filename="unexpected.txt",
                    content_type="text/plain",
                    size_bytes=3,
                    storage_path="approved/file",
                    sha256="a" * 64,
                )
            )
    with pytest.raises(HTTPException) as refused:
        await session.flush()
    assert refused.value.status_code == 409


async def test_snapshot_keeps_body_scope_sections_files_signoffs_and_not_execution_hash(session):
    from app.models import ArtefactTag, Tag
    from app.services.document_workflow import (
        content_hash,
        content_snapshot,
        get_workflow,
    )

    row = await _saved(session, "SPEC", "Draft")
    row.description = "Approved body"
    session.add(Tag(name="original"))
    await session.flush()
    session.add(ArtefactTag(tag_id=1, artefact_type="document", artefact_id=row.id, project_id=1))
    session.add(DocumentSection(document_id=row.id, title="Section", content="Section body"))
    session.add(
        DocumentAttachment(
            document_id=row.id,
            filename="proof.txt",
            original_filename="proof.txt",
            content_type="text/plain",
            size_bytes=3,
            storage_path="approved/proof",
            sha256="a" * 64,
            uploaded_by_id=1,
        )
    )
    await session.flush()
    workflow = await get_workflow(session, row)
    snapshot = await content_snapshot(session, row)
    assert snapshot["fields"]["description"] == "Approved body"
    assert snapshot["fields"]["visibility"] == "internal"
    assert snapshot["tag_ids"] == [1]
    assert snapshot["sections"][0]["content"] == "Section body"
    assert snapshot["attachments"][0]["storage_path"] == "approved/proof"
    assert snapshot["signoffs"]["approved_by_id"] is None
    assert workflow.phase == "Draft"
    case = await _saved(session, "TC")
    before = content_hash(await content_snapshot(session, case))
    case.last_execution_status = "Passed"
    case.last_bud_run_id = 123
    await session.flush()
    assert content_hash(await content_snapshot(session, case)) == before


async def test_capture_is_idempotent_keeps_nullable_history_and_immutable_file_refs(session):
    from app.models.workflow import ArtefactRevisionFile
    from app.services.document_workflow import (
        capture_revision,
        get_workflow,
        permit_workflow_write,
    )

    row = await _saved(session, "SPEC", "Draft")
    session.add(
        DocumentAttachment(
            document_id=row.id,
            filename="proof.txt",
            original_filename="proof.txt",
            content_type="text/plain",
            size_bytes=3,
            storage_path="approved/proof",
            sha256="a" * 64,
        )
    )
    await session.flush()
    workflow = await get_workflow(session, row)
    with permit_workflow_write(session, row):
        row.status = "Approved"
        workflow.phase = "Approved"
        await session.flush()
    revision = await capture_revision(session, row, workflow)
    assert await capture_revision(session, row, workflow) is revision
    assert revision.approved_by_id is None
    assert revision.approved_at is None
    assert revision.content_snapshot["signoffs"]["approved_by_id"] is None
    file = (await session.execute(select(ArtefactRevisionFile))).scalar_one()
    assert file.storage_path == "approved/proof"
    file.storage_path = "overwritten"
    with pytest.raises(HTTPException) as refused:
        await session.flush()
    assert refused.value.status_code == 409


@pytest.mark.parametrize("operation", ["edit", "delete"])
async def test_approved_archive_cannot_be_mutated(session, operation):
    from app.services.document_workflow import capture_revision, get_workflow

    row = await _saved(session, "REQ")
    revision = await capture_revision(session, row, await get_workflow(session, row))
    if operation == "edit":
        revision.content_snapshot = {"fields": {"title": "Rewritten"}}
    else:
        await session.delete(revision)
    with pytest.raises(HTTPException) as refused:
        await session.flush()
    assert refused.value.status_code == 409


async def test_review_content_edit_supersedes_request_and_returns_draft(session):
    from app.models.workflow import ArtefactRequest
    from app.services.document_workflow import (
        content_hash,
        content_snapshot,
        get_workflow,
        prepare_content_write,
    )

    row = await _saved(session, "REQ", "Review")
    workflow = await get_workflow(session, row)
    request = ArtefactRequest(
        workflow_id=workflow.id,
        revision_number=1,
        kind="review",
        requester_id=1,
        content_hash=content_hash(await content_snapshot(session, row)),
        status="pending",
    )
    session.add(request)
    await session.flush()
    await prepare_content_write(session, row, await session.get(User, 1), {"title": "Changed"})
    row.title = "Changed"
    await session.flush()
    assert row.status == workflow.phase == "Draft"
    assert request.status == "superseded"
    assert request.decided_by_id == 1
    assert request.decided_at is not None
    assert workflow.review_content_hash is None


async def test_explicit_revision_changes_working_row_but_preserves_archive_and_baseline(session):
    from app.models import Baseline
    from app.services.document_workflow import (
        capture_revision,
        get_workflow,
        permit_workflow_write,
    )

    row = await _saved(session, "REQ")
    session.add(Baseline(project_id=1, name="Original", snapshot={"title": "Frozen baseline"}))
    await session.flush()
    workflow = await get_workflow(session, row)
    revision = await capture_revision(session, row, workflow)
    with permit_workflow_write(session, row):
        row.status = "Draft"
        workflow.phase = "Draft"
        workflow.revision_number += 1
        workflow.revision_creator_id = 1
        await session.flush()
    row.title = "Next draft"
    await session.flush()
    assert revision.content_snapshot["fields"]["title"] == "Original"
    assert (await session.execute(select(Baseline))).scalar_one().snapshot == {
        "title": "Frozen baseline"
    }


async def test_approved_change_remains_frozen_even_with_workflow_permit(session):
    from app.services.document_workflow import permit_workflow_write

    row = await _saved(session, "CHG")
    with permit_workflow_write(session, row):
        row.status = "Draft"
        with pytest.raises(HTTPException) as refused:
            await session.flush()
    assert refused.value.status_code == 409


@pytest.mark.parametrize("kind,status", [("CHG", "Implemented"), ("REQ", "Verified")])
async def test_unsupported_status_does_not_fabricate_a_workflow(session, kind, status):
    from app.models.workflow import ArtefactWorkflow
    from app.services.document_workflow import get_workflow

    row = await _saved(session, kind, status)
    with pytest.raises(HTTPException) as refused:
        await get_workflow(session, row)
    assert refused.value.status_code == 409
    assert await session.scalar(select(ArtefactWorkflow)) is None
    assert row.status == status
    row.title = "Still working legacy proposal"
    await session.flush()


async def test_exception_operational_status_and_authored_writes_remain_legal(session):
    row = RiskItem(project_id=1, risk_id="WFL-RSK-001", title="Operational", status="Closed")
    session.add(row)
    await session.commit()
    row.status = "Open"
    row.title = "Updated operational record"
    await session.flush()


@pytest.mark.parametrize("scope", ["visibility", "req_origin", "tag"])
async def test_review_scope_change_supersedes_pending_content_hash(session, scope):
    from app.models import ArtefactTag, Tag
    from app.models.workflow import ArtefactRequest
    from app.services.document_workflow import (
        content_hash,
        content_snapshot,
        get_workflow,
    )

    row = await _saved(session, "REQ", "Review")
    workflow = await get_workflow(session, row)
    request = ArtefactRequest(
        workflow_id=workflow.id,
        revision_number=1,
        kind="review",
        requester_id=1,
        content_hash=content_hash(await content_snapshot(session, row)),
        status="pending",
    )
    session.add(request)
    await session.flush()
    if scope == "tag":
        session.add(Tag(name="changed-scope"))
        await session.flush()
        session.add(
            ArtefactTag(tag_id=1, artefact_type="requirement", artefact_id=row.id, project_id=1)
        )
    else:
        setattr(row, scope, "customer" if scope == "visibility" else "External")
    await session.flush()
    assert row.status == workflow.phase == "Draft"
    assert request.status == "superseded"
    assert request.decided_at is not None


async def test_approved_scope_and_tracker_transport_remain_legal_with_archive_scope_preserved(
    session,
):
    from app.services.document_workflow import (
        capture_revision,
        content_hash,
        content_snapshot,
        get_workflow,
    )

    row = await _saved(session, "REQ")
    revision = await capture_revision(session, row, await get_workflow(session, row))
    row.visibility = "customer"
    row.req_origin = "External"
    await session.flush()
    assert revision.content_snapshot["fields"]["visibility"] == "internal"
    assert revision.content_snapshot["fields"]["req_origin"] == "Internal"
    change = await _saved(session, "CHG")
    before = content_hash(await content_snapshot(session, change))
    change.external_issue_state = "closed"
    change.external_last_event_at = None
    await session.flush()
    assert content_hash(await content_snapshot(session, change)) == before


async def test_controlled_identity_accepts_legacy_concept_and_protocol_aliases(session):
    from app.services.document_workflow import artefact_identity, controlled

    concept = Concept(project_id=1, concept_id="WFL-TCO-001", name="Legacy concept")
    protocol = Document(
        project_id=1, doc_id="WFL-PROT-001", doc_type="PROT", title="Legacy protocol"
    )
    assert artefact_identity(concept) == ("test-concept", "CPT")
    assert artefact_identity(protocol) == ("document", "PRT")
    assert controlled(concept)
    assert controlled(protocol)


async def test_approved_document_cannot_bypass_guard_by_changing_kind(session):
    row = await _saved(session, "SPEC")
    row.doc_type = "RPT"
    row.description = "Bypass"
    with pytest.raises(HTTPException) as refused:
        await session.flush()
    assert refused.value.status_code == 409


@pytest.mark.parametrize("change", ["body", "section"])
async def test_unguarded_review_authored_write_invalidates_cycle(session, change):
    from app.models.workflow import ArtefactRequest
    from app.services.audit import audit_actor_var
    from app.services.document_workflow import (
        content_hash,
        content_snapshot,
        get_workflow,
    )

    row = await _saved(session, "SPEC", "Review")
    workflow = await get_workflow(session, row)
    request = ArtefactRequest(
        workflow_id=workflow.id,
        revision_number=1,
        kind="review",
        requester_id=1,
        content_hash=content_hash(await content_snapshot(session, row)),
        status="pending",
    )
    session.add(request)
    await session.flush()
    token = audit_actor_var.set(("user", 1))
    try:
        if change == "body":
            row.description = "Changed body"
        else:
            session.add(DocumentSection(document_id=row.id, title="Changed section"))
        await session.flush()
    finally:
        audit_actor_var.reset(token)
    assert row.status == workflow.phase == "Draft"
    assert request.status == "superseded"
    assert request.decided_by_id == 1


async def test_prepared_scope_edit_allows_approved_and_invalidates_review(session):
    from app.services.document_workflow import get_workflow, prepare_content_write

    row = await _saved(session, "REQ", "Review")
    workflow = await get_workflow(session, row)
    await prepare_content_write(
        session, row, await session.get(User, 1), {"req_origin": "External"}
    )
    row.req_origin = "External"
    await session.flush()
    assert row.status == workflow.phase == "Draft"
    approved = await _saved(session, "SPEC")
    await prepare_content_write(
        session, approved, await session.get(User, 1), {"visibility": "customer"}
    )
    approved.visibility = "customer"
    await session.flush()
    assert approved.status == "Approved"
