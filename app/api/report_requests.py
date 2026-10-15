"""Reader report requests and the authenticated Bud publishing mailbox."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import get_visible_row
from app.api.test_suites import _build_suite_response
from app.core.database import get_db
from app.core.security import doc_type_visible, get_current_user
from app.core.service_auth import require_bud_sync_token
from app.models import (
    Document,
    Project,
    ReportRequest,
    Requirement,
    TestCampaign,
    TestCase,
    TestRunLink,
    TestSuite,
)
from app.models.user import User
from app.services.audit import record_audit_event

router = APIRouter()
SourceKind = Literal["test-case", "test-suite", "requirement", "campaign"]
SOURCES = {
    "test-case": (TestCase, "TC"),
    "test-suite": (TestSuite, "TS"),
    "requirement": (Requirement, "REQ"),
    "campaign": (TestCampaign, "CMP"),
}


class ReaderRequest(BaseModel):
    """An existing visible source and its linked run."""

    source_kind: SourceKind
    source_id: int = Field(gt=0)
    run_id: int = Field(gt=0)


class Refusal(BaseModel):
    """A Bud publisher's refusal and attribution."""

    reason: str = Field(min_length=1, max_length=2000)
    publisher: str = Field(min_length=1, max_length=300)


async def visible_source(db: AsyncSession, user: User, data: ReaderRequest):
    """The visible source only when it records the requested run."""
    model, resource = SOURCES[data.source_kind]
    row = await get_visible_row(
        db, model, data.source_id, "Source not found", user, permission=("view", resource)
    )
    if data.source_kind == "test-case":
        linked = row.last_bud_run_id == data.run_id
    elif data.source_kind == "campaign":
        linked = row.bud_run_id == data.run_id
    elif data.source_kind == "test-suite":
        suite = await _build_suite_response(
            row, db, user, await doc_type_visible(db, user, row.project_id, "TC")
        )
        linked = suite.last_bud_run_id == data.run_id
    else:
        linked = await db.scalar(
            select(TestRunLink.id).where(
                TestRunLink.requirement_id == row.id, TestRunLink.test_run_id == data.run_id
            )
        )
    if not linked:
        raise HTTPException(status_code=404, detail="Linked run not found")
    return row


async def reader_response(db: AsyncSession, user: User, row: ReportRequest | None):
    """Request state with a report link only when that report is visible."""
    if row is None:
        return None
    document = None
    if row.document_id:
        try:
            document = await get_visible_row(
                db,
                Document,
                row.document_id,
                "Report not found",
                user,
                permission=("view", None),
            )
        except HTTPException as exc:
            if exc.status_code not in (403, 404):
                raise
    project = await db.get(Project, row.project_id)
    return {
        "id": row.id,
        "status": row.status,
        "reason": row.reason,
        "project_prefix": project.prefix,
        "doc_id": document.doc_id if document else None,
    }


@router.get("/report-requests")
async def request_state(
    source_kind: SourceKind,
    source_id: int = Query(gt=0),
    run_id: int = Query(gt=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    """The current reader's most recent request for a visible linked run."""
    source = await visible_source(
        db, user, ReaderRequest(source_kind=source_kind, source_id=source_id, run_id=run_id)
    )
    row = await db.scalar(
        select(ReportRequest)
        .where(
            ReportRequest.project_id == source.project_id,
            ReportRequest.bud_run_id == run_id,
            ReportRequest.requester_id == user.id,
        )
        .order_by(ReportRequest.id.desc())
        .limit(1)
    )
    return await reader_response(db, user, row)


@router.post("/report-requests", status_code=201)
async def request_report(
    data: ReaderRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    """Persist one pending request per reader, project and linked run."""
    source = await visible_source(db, user, data)
    pending_query = select(ReportRequest).where(
        ReportRequest.project_id == source.project_id,
        ReportRequest.bud_run_id == data.run_id,
        ReportRequest.requester_id == user.id,
        ReportRequest.status == "pending",
    )
    row = await db.scalar(pending_query)
    if row is None:
        row = ReportRequest(
            project_id=source.project_id, bud_run_id=data.run_id, requester_id=user.id
        )
        db.add(row)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            row = (await db.execute(pending_query)).scalar_one()
        else:
            await record_audit_event(
                db,
                "report.requested",
                target_type="report_request",
                target_id=row.id,
                project_id=row.project_id,
            )
        await db.commit()
    return await reader_response(db, user, row)


@router.get("/bud/report-requests")
async def publishing_mailbox(
    after_id: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    request_ids: list[int] | None = Query(default=None, max_length=100),
    _credential=Depends(require_bud_sync_token),
):
    """A bounded page of requests for the configured Bud report publisher."""
    rows = (
        await db.execute(
            select(ReportRequest, Project.prefix, User.full_name, User.email)
            .join(Project, Project.id == ReportRequest.project_id)
            .join(User, User.id == ReportRequest.requester_id)
            .where(
                ReportRequest.id.in_(request_ids)
                if request_ids is not None
                else ReportRequest.id > after_id
            )
            .order_by(ReportRequest.id)
            .limit(100)
        )
    ).all()
    return [
        {
            "id": row.id,
            "run_id": row.bud_run_id,
            "project_prefix": prefix,
            "requester_name": name,
            "requester_email": email,
            "status": row.status,
            "reason": row.reason,
        }
        for row, prefix, name, email in rows
    ]


@router.post("/bud/report-requests/{request_id}/refuse")
async def refuse_report(
    request_id: int,
    data: Refusal,
    db: AsyncSession = Depends(get_db, scope="function"),
    _credential=Depends(require_bud_sync_token),
):
    """Record an authenticated publisher's refusal without replacing a delivery."""
    row = await db.scalar(
        select(ReportRequest).where(ReportRequest.id == request_id).with_for_update()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if row.status == "delivered":
        raise HTTPException(status_code=409, detail="The report has already been delivered")
    reason = data.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="A refusal reason is required")
    if row.status == "pending":
        row.status = "refused"
        row.reason = reason
        row.publisher = data.publisher
        row.updated_at = datetime.utcnow()
        await record_audit_event(
            db,
            "report.refused",
            target_type="report_request",
            target_id=row.id,
            project_id=row.project_id,
            details={"reason": row.reason, "bud_publisher": row.publisher},
        )
        await db.commit()
    return {"status": row.status}
