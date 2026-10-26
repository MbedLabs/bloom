"""Content-bound document handoffs and preserved approved revisions."""

from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    artefact_public_id,
    changes_allowed,
    check_external_change,
    get_artefact_or_404,
    get_visible_row,
    may_sign_as,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.security import covers_with_tags, get_current_user, row_allows
from app.models import (
    ArtefactActivity,
    ArtefactComment,
    ArtefactRequest,
    ArtefactRequestRecipient,
    ArtefactRevision,
    ArtefactRevisionFile,
    ArtefactWorkflow,
    ChangeRequest,
    Project,
    Requirement,
    TestCase,
)
from app.models.user import User, UserRole
from app.services import attachment_storage, object_store
from app.services.audit import record_audit_event
from app.services.document_workflow import (
    artefact_identity,
    capture_revision,
    content_hash,
    content_snapshot,
    controlled,
    get_workflow,
    permit_workflow_write,
    recorded_phase,
)
from app.services.mail_service import (
    MailConfigurationError,
    send_workflow_request_email,
)
from app.services.notification_service import notify, notify_assignment

THIS_DOCUMENT_HAS_NO_APPROVAL_WORKFLOW = "This document has no approval workflow."

router = APIRouter()
REQUEST_WINDOW = timedelta(hours=24)
DOC_SLUGS = {
    "REQ": "requirements",
    "SPEC": "specifications",
    "TC": "test-cases",
    "DES": "designs",
    "RSK": "risks",
    "CHG": "changes",
    "CPT": "test-concepts",
    "DEF": "defects",
    "CMP": "campaigns",
    "TS": "test-suites",
    "PRT": "protocols",
    "RPT": "reports",
    "STD": "standards",
}


class Assignees(BaseModel):
    """Explicit assignee, reviewer and approver selections for one document."""

    model_config = ConfigDict(extra="forbid")
    assignee_id: int | None = None
    reviewer_id: int | None = None
    approver_id: int | None = None


class RevisionStart(BaseModel):
    """An approved change authorizing a new working revision."""

    model_config = ConfigDict(extra="forbid")
    change_request_id: int


class RequestStart(BaseModel):
    """The requested review or approval handoff."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["review", "approval"]


def _time(value):
    """Serialize a recorded server timestamp as UTC."""
    return value.isoformat() + "Z" if value else None


async def _person(db, user_id):
    """Return the recorded account identity when the account exists."""
    user = await db.get(User, user_id) if user_id else None
    return (
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "profile_picture_url": user.profile_picture_url,
        }
        if user
        else None
    )


def assigned_id(row, workflow, step):
    """Read the authoritative assignee from the document or its workflow."""
    field = "reviewer_id" if step == "review" else "approver_id"
    return getattr(row, field) if hasattr(row, field) else getattr(workflow, field)


async def visible_artefact(db, slug, identifier, user, action="view", lock=False):
    """Load a visible document and recheck its complete row scope before acting."""
    row = await get_artefact_or_404(db, slug, identifier, user)
    _, code = artefact_identity(row)
    row = await get_visible_row(
        db, type(row), row.id, "Artefact not found", user, permission=(action, code)
    )
    if not await row_allows(db, user, row, "view", code):
        raise HTTPException(status_code=404, detail="Artefact not found")
    if lock:
        row = await db.scalar(select(type(row)).where(type(row).id == row.id).with_for_update())
    return row


def may_change_assignee(user, row, state, assign) -> bool:
    """The creator, the current assignee and whoever may assign the reviewer change the
    assignee."""
    return assign or user.id in {getattr(row, "created_by_id", None), state.assignee_id}


async def _may_take_document(db, person, row) -> bool:
    """An assignee sees the document and may change it."""
    code = artefact_identity(row)[1]
    return (
        person.is_active
        and changes_allowed(person, row)
        and await row_allows(db, person, row, "view", code)
        and await row_allows(db, person, row, "edit", code)
    )


async def _may_sign(db, user, row, step):
    """Check existing authority and visibility for this particular document."""
    return user.is_active and await may_sign_as(
        db, user, row.project_id, artefact_identity(row)[1], step, row
    )


def _co_authors(row, workflow) -> set[int]:
    """A controlled document's creator, assignee and approver; empty for other types."""
    if not controlled(row):
        return set()
    assignee = workflow.assignee_id if workflow else getattr(row, "created_by_id", None)
    approver = (
        assigned_id(row, workflow, "approve") if workflow or hasattr(row, "approver_id") else None
    )
    return {
        person for person in (getattr(row, "created_by_id", None), assignee, approver) if person
    }


def comment_participants(row, workflow) -> set[int]:
    """The people who take part in a document's discussion: its reviewer, and for a
    controlled document also its creator, assignee and approver."""
    reviewer = (
        assigned_id(row, workflow, "review") if workflow or hasattr(row, "reviewer_id") else None
    )
    return _co_authors(row, workflow) | ({reviewer} if reviewer else set())


async def can_comment(db, user, row):
    """Allow the visible document's assigned reviewer to comment, and on a controlled
    document not yet Approved also its creator, assignee and approver."""
    if not user.is_active or not await row_allows(db, user, row, "view"):
        return False
    workflow = await get_workflow(db, row, create=False)
    reviewer = (
        assigned_id(row, workflow, "review") if workflow or hasattr(row, "reviewer_id") else None
    )
    if reviewer == user.id and await row_allows(db, user, row, "review"):
        return True
    phase = workflow.phase if workflow else recorded_phase(row.status)
    return phase != "Approved" and user.id in _co_authors(row, workflow)


async def document_path(db, row) -> str:
    """The application path of a document's page."""
    slug, code = artefact_identity(row)
    project = await db.get(Project, row.project_id)
    return f"/projects/{project.prefix}/docs/{DOC_SLUGS[code]}/{artefact_public_id(slug, row)}"


async def _pending(db, state, kind=None):
    """Find the current revision's pending handoff."""
    query = select(ArtefactRequest).where(
        ArtefactRequest.workflow_id == state.id,
        ArtefactRequest.revision_number == state.revision_number,
        ArtefactRequest.status == "pending",
    )
    if kind:
        query = query.where(ArtefactRequest.kind == kind)
    return await db.scalar(query.order_by(ArtefactRequest.created_at.desc()).limit(1))


async def _review_request(db, state):
    """Find the review whose unchanged content can proceed to approval."""
    return await db.scalar(
        select(ArtefactRequest)
        .where(
            ArtefactRequest.workflow_id == state.id,
            ArtefactRequest.revision_number == state.revision_number,
            ArtefactRequest.kind == "review",
            ArtefactRequest.status.in_(["pending", "answered"]),
        )
        .order_by(ArtefactRequest.created_at.desc())
        .limit(1)
    )


async def _review_proof(db, row, state, actor, fingerprint):
    """Require the assigned reviewer's comment on the current review request."""
    request = await _review_request(db, state)
    if not request or request.content_hash != fingerprint:
        raise HTTPException(status_code=409, detail="The current content needs review.")
    comment = await db.scalar(
        select(ArtefactComment.id)
        .where(
            ArtefactComment.artefact_type == state.artefact_type,
            ArtefactComment.artefact_id == row.id,
            ArtefactComment.author_user_id == actor.id,
            ArtefactComment.revision_number == state.revision_number,
            ArtefactComment.content_hash == fingerprint,
            ArtefactComment.review_request_id == request.id,
        )
        .limit(1)
    )
    if not comment:
        raise HTTPException(
            status_code=409, detail="Comment on this review before requesting approval."
        )
    return request


async def _recipients(db, row, state, step):
    """Select active, visible accounts with existing authority for the handoff."""
    selected = assigned_id(row, state, step)
    assignee = await db.get(User, selected) if selected else None
    if assignee and await _may_sign(db, assignee, row, step):
        return [assignee]
    query = select(User).where(User.is_active.is_(True))
    return [
        person
        for person in (await db.scalars(query.order_by(User.id))).all()
        if await _may_sign(db, person, row, step)
    ]


async def _delivered_actor(db, row, state, request, user):
    """Check current authority, recorded delivery and any eligible explicit assignee."""
    if request is None:
        return False
    step = "review" if request.kind == "review" else "approve"
    if not await db.get(ArtefactRequestRecipient, (request.id, user.id)) or not await _may_sign(
        db, user, row, step
    ):
        return False
    selected = assigned_id(row, state, step)
    if not selected or selected == user.id:
        return True
    assignee = await db.get(User, selected)
    return not (assignee and await _may_sign(db, assignee, row, step))


async def request_handoff(db, row, user, kind):
    """Deliver a content-bound request and record only actual review completion."""
    state = await get_workflow(db, row)
    if not controlled(row):
        raise HTTPException(status_code=409, detail=THIS_DOCUMENT_HAS_NO_APPROVAL_WORKFLOW)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    previous = await db.scalar(
        select(ArtefactRequest)
        .where(
            ArtefactRequest.workflow_id == state.id,
            ArtefactRequest.revision_number == state.revision_number,
            ArtefactRequest.kind == kind,
            ArtefactRequest.requester_id == user.id,
            ArtefactRequest.created_at > now - REQUEST_WINDOW,
        )
        .order_by(ArtefactRequest.created_at.desc())
        .limit(1)
    )
    if previous:
        return {
            "id": previous.id,
            "status": previous.status,
            "already_requested": True,
            "retry_at": _time(previous.created_at + REQUEST_WINDOW),
        }, False
    fingerprint = content_hash(await content_snapshot(db, row))
    review = None
    if kind == "review":
        if state.assignee_id != user.id:
            raise HTTPException(
                status_code=403, detail="Only the document's assignee requests review."
            )
        if state.phase != "Draft" or row.status != "Draft":
            raise HTTPException(status_code=409, detail="Review starts from Draft.")
        recipients = await _recipients(db, row, state, "review")
    else:
        if assigned_id(row, state, "review") != user.id or not await _may_sign(
            db, user, row, "review"
        ):
            raise HTTPException(
                status_code=403, detail="Only the assigned reviewer requests approval."
            )
        if state.phase != "Review":
            raise HTTPException(status_code=409, detail="Approval needs a current review.")
        review = await _review_proof(db, row, state, user, fingerprint)
        recipients = await _recipients(db, row, state, "approve")
    if not recipients:
        raise HTTPException(
            status_code=409, detail="No eligible recipient can see and act on this document."
        )
    request = ArtefactRequest(
        workflow_id=state.id,
        revision_number=state.revision_number,
        kind=kind,
        requester_id=user.id,
        content_hash=fingerprint,
        status="pending",
        created_at=now,
    )
    with permit_workflow_write(db, row):
        if kind == "review":
            state.phase = row.status = "Review"
        else:
            if review.status == "pending":
                review.status = "answered"
                review.decided_by_id = user.id
                review.decided_at = now
            state.reviewed_by_id = user.id
            state.reviewed_at = now
            state.review_content_hash = fingerprint
            state.phase = "Approval"
            if hasattr(row, "reviewed_by_id"):
                row.reviewed_by_id = user.id
                row.reviewed_at = now
        db.add(request)
        await db.flush()
    for person in recipients:
        db.add(ArtefactRequestRecipient(request_id=request.id, user_id=person.id))
        await _deliver(db, row, request, person, user)
    await _event(db, state, user, "requested", request, kind=kind)
    if review and review.decided_by_id == user.id:
        await _event(db, state, user, "reviewed", review)
    return {
        "id": request.id,
        "status": request.status,
        "already_requested": False,
        "retry_at": _time(now + REQUEST_WINDOW),
    }, True


async def complete_step(db, row, user, step):
    """Complete a reviewed handoff using its real actor, content and server time."""
    state = await get_workflow(db, row)
    if step == "review":
        await request_handoff(db, row, user, "approval")
        return state
    if not controlled(row):
        raise HTTPException(status_code=409, detail=THIS_DOCUMENT_HAS_NO_APPROVAL_WORKFLOW)
    request = await _pending(db, state, "approval")
    fingerprint = content_hash(await content_snapshot(db, row))
    if (
        state.phase != "Approval"
        or not request
        or request.content_hash != fingerprint
        or state.review_content_hash != fingerprint
    ):
        raise HTTPException(
            status_code=409, detail="Approval requires an unchanged, reviewed approval request."
        )
    if not await _delivered_actor(db, row, state, request, user):
        raise HTTPException(
            status_code=403, detail="This approval request is not assigned or delivered to you."
        )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with permit_workflow_write(db, row):
        request.status = "answered"
        request.decided_by_id = user.id
        request.decided_at = now
        state.phase = row.status = "Approved"
        state.approved_by_id = user.id
        state.approved_at = now
        if hasattr(row, "approved_by_id"):
            row.approved_by_id = user.id
            row.approved_at = now
        await db.flush()
    await capture_revision(db, row, state)
    await _event(db, state, user, "approved", request)
    requester = await db.get(User, request.requester_id) if request.requester_id else None
    if requester and requester.is_active:
        await _deliver(db, row, request, requester, user, "approved")
    return state


async def _change(db, change_id, user):
    """Expose approved authorizing changes only when currently visible."""
    change = await db.get(ChangeRequest, change_id) if change_id else None
    if change and await row_allows(db, user, change, "view", "CHG"):
        return {"id": change.id, "change_id": change.change_id, "title": change.title}
    return None


async def _event(db, state, actor, event, request=None, **details):
    """Record an actual workflow actor and server-side result."""
    await record_audit_event(
        db,
        f"workflow.{event}",
        target_type=state.artefact_type,
        target_id=state.artefact_id,
        project_id=state.project_id,
        actor_user_id=actor.id,
        details={
            "revision": state.revision_number,
            "request_id": request.id if request else None,
            **details,
        },
    )
    activity_type = f"{details['kind']}_requested" if event == "requested" else event
    action = {
        "requested": f"requested {details.get('kind', '')}",
        "reviewed": "reviewed this document",
        "approved": "approved this document",
        "declined": f"declined {request.kind}" if request else "declined the request",
        "assigned": "updated the document assignments",
        "draft_started": "started a working Draft",
        "revision_started": "started a new working revision",
    }[event]
    db.add(
        ArtefactActivity(
            artefact_type=state.artefact_type,
            artefact_id=state.artefact_id,
            event_type=activity_type,
            summary=f"{actor.full_name} {action}",
            actor_user_id=actor.id,
        )
    )
    await db.flush()


async def workflow_response(db, row, user):
    """Return the visible current state and actions derived from existing IAM."""
    is_controlled = controlled(row)
    state = await get_workflow(db, row, create=False)
    if state is None:
        if is_controlled and recorded_phase(row.status) is None:
            slug, _ = artefact_identity(row)
            state = ArtefactWorkflow(
                project_id=row.project_id,
                artefact_type=slug,
                artefact_id=row.id,
                phase=None,
                revision_number=None,
                revision_creator_id=getattr(row, "created_by_id", None),
                assignee_id=getattr(row, "created_by_id", None),
                **{
                    field: getattr(row, field, None)
                    for field in (
                        "reviewer_id",
                        "approver_id",
                        "reviewed_by_id",
                        "reviewed_at",
                        "approved_by_id",
                        "approved_at",
                    )
                },
            )
        else:
            state = await get_workflow(db, row)
    code = artefact_identity(row)[1]
    pending = await _pending(db, state)
    reviewer_id = assigned_id(row, state, "review")
    approver_id = assigned_id(row, state, "approve")
    edit = changes_allowed(user, row) and await row_allows(db, user, row, "edit", code)
    mutable = not is_controlled or code != "CHG" or row.status != "Approved"
    can_review = user.id == reviewer_id and await _may_sign(db, user, row, "review")
    delivered_actor = await _delivered_actor(db, row, state, pending, user)
    fingerprint = content_hash(await content_snapshot(db, row))
    review_request = await _review_request(db, state)
    review_comment = bool(
        review_request
        and await db.scalar(
            select(ArtefactComment.id)
            .where(
                ArtefactComment.artefact_type == state.artefact_type,
                ArtefactComment.artefact_id == row.id,
                ArtefactComment.author_user_id == user.id,
                ArtefactComment.review_request_id == review_request.id,
                ArtefactComment.revision_number == state.revision_number,
                ArtefactComment.content_hash == fingerprint,
            )
            .limit(1)
        )
    )
    eligible_reviewers, eligible_approvers = [], []
    assign = edit and user.role != UserRole.external and state.id is not None
    assign_assignee = bool(
        is_controlled
        and edit
        and state.id is not None
        and may_change_assignee(user, row, state, assign)
    )
    eligible_assignees = []
    if assign_assignee:
        for person in (
            await db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.full_name))
        ).all():
            if await _may_take_document(db, person, row):
                eligible_assignees.append(await _person(db, person.id))
    if assign:
        for person in (
            await db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.full_name))
        ).all():
            visible = await row_allows(db, person, row, "view", code)
            if visible and await _may_sign(db, person, row, "review"):
                eligible_reviewers.append(await _person(db, person.id))
            if is_controlled and visible and await _may_sign(db, person, row, "approve"):
                eligible_approvers.append(await _person(db, person.id))
    changes = []
    revisions = []
    for revision in (
        await db.scalars(
            select(ArtefactRevision)
            .where(ArtefactRevision.workflow_id == state.id)
            .order_by(ArtefactRevision.revision_number.desc())
        )
    ).all():
        if await _revision_visible(db, row, revision, user):
            change = await _change(db, revision.authorizing_change_id, user)
            revisions.append(
                {
                    "revision_number": revision.revision_number,
                    "captured_at": _time(revision.captured_at),
                    "approved_by": await _person(db, revision.approved_by_id),
                    "approved_at": _time(revision.approved_at),
                    "authorizing_change_id": change["id"] if change else None,
                }
            )
    last = await db.scalar(
        select(ArtefactRequest)
        .where(
            ArtefactRequest.workflow_id == state.id,
            ArtefactRequest.revision_number == state.revision_number,
        )
        .order_by(ArtefactRequest.created_at.desc())
        .limit(1)
    )
    return {
        "controlled": is_controlled,
        "revision_number": state.revision_number,
        "phase": state.phase,
        "status": row.status,
        "creator": await _person(db, state.revision_creator_id),
        "created_by": await _person(db, getattr(row, "created_by_id", None)),
        "assignee": await _person(db, state.assignee_id if is_controlled else None),
        "reviewer": await _person(db, reviewer_id),
        "approver": await _person(db, approver_id),
        "reviewed_by": await _person(db, state.reviewed_by_id),
        "reviewed_at": _time(state.reviewed_at),
        "approved_by": await _person(db, state.approved_by_id),
        "approved_at": _time(state.approved_at),
        "authorizing_change": await _change(db, state.authorizing_change_id, user),
        "options": {
            "assignees": eligible_assignees,
            "reviewers": eligible_reviewers,
            "approvers": eligible_approvers,
            "changes": changes,
        },
        "actions": {
            "request_review": bool(
                is_controlled and state.phase == "Draft" and state.assignee_id == user.id
            ),
            "assign_assignee": assign_assignee,
            "request_approval": bool(
                is_controlled
                and state.phase == "Review"
                and can_review
                and review_comment
                and review_request.content_hash == fingerprint
            ),
            "approve": bool(
                is_controlled
                and state.phase == "Approval"
                and pending
                and pending.kind == "approval"
                and delivered_actor
                and state.review_content_hash == fingerprint
            ),
            "decline": bool(pending and delivered_actor),
            "assign_reviewer": assign,
            "assign_approver": assign and is_controlled,
            "comment": await can_comment(db, user, row),
            "start_revision": False,
            "start_draft": bool(
                is_controlled
                and edit
                and row.status != "Approved"
                and (state.revision_creator_id is None or row.status not in {"Draft", "Review"})
            ),
            "edit_current": edit and mutable,
            "plan_current": mutable and await row_allows(db, user, row, "plan", code),
        },
        "pending_request": (
            {
                "id": pending.id,
                "kind": pending.kind,
                "status": pending.status,
                "created_at": _time(pending.created_at),
            }
            if pending
            else None
        ),
        "last_request": (
            {
                "id": last.id,
                "kind": last.kind,
                "status": last.status,
                "retry_at": _time(last.created_at + REQUEST_WINDOW),
            }
            if last
            else None
        ),
        "revisions": revisions,
    }


@router.get(
    "/artefacts/{slug}/{identifier}/workflow",
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def read_workflow(
    slug: str,
    identifier: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    row = await visible_artefact(db, slug, identifier, user)
    return await workflow_response(db, row, user)


@router.put(
    "/artefacts/{slug}/{identifier}/workflow/assignees",
    responses={
        404: {"description": HTTPStatus(404).phrase},
        422: {"description": HTTPStatus(422).phrase},
    },
)
async def set_assignees(
    slug: str,
    identifier: str,
    data: Assignees,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    row = await visible_artefact(db, slug, identifier, user, "edit", lock=True)
    state = await get_workflow(db, row)
    values = data.model_dump(exclude_unset=True)
    check_external_change(user, artefact_identity(row)[1], row, values)
    if "assignee_id" in values:
        await _set_assignee(db, row, state, user, values.pop("assignee_id"))
    for field, person_id in values.items():
        step = "review" if field == "reviewer_id" else "approve"
        if step == "approve" and not controlled(row):
            raise HTTPException(status_code=422, detail=THIS_DOCUMENT_HAS_NO_APPROVAL_WORKFLOW)
        person = await db.get(User, person_id) if person_id else None
        if person_id and (
            person is None
            or not person.is_active
            or not await row_allows(db, person, row, "view")
            or not await _may_sign(db, person, row, step)
        ):
            raise HTTPException(
                status_code=422, detail="The assignee cannot see or act on this document."
            )
        setattr(row if hasattr(row, field) else state, field, person_id)
        pending = await _pending(db, state, step if step == "review" else "approval")
        if (
            pending
            and person
            and not await db.get(ArtefactRequestRecipient, (pending.id, person.id))
        ):
            db.add(ArtefactRequestRecipient(request_id=pending.id, user_id=person.id))
            await _deliver(db, row, pending, person, user)
    await db.flush()
    await _event(db, state, user, "assigned", **data.model_dump(exclude_unset=True))
    return await workflow_response(db, row, user)


async def _set_assignee(db, row, state, user, person_id) -> None:
    """Hand a controlled document to another assignee and notify them."""
    if not controlled(row):
        raise HTTPException(status_code=422, detail=THIS_DOCUMENT_HAS_NO_APPROVAL_WORKFLOW)
    assign = user.role != UserRole.external
    if not may_change_assignee(user, row, state, assign):
        raise HTTPException(
            status_code=403,
            detail="Only the creator, the assignee or a reviewer assigner changes the assignee.",
        )
    person = await db.get(User, person_id) if person_id else None
    if person is None or not await _may_take_document(db, person, row):
        raise HTTPException(
            status_code=422, detail="The assignee cannot see or edit this document."
        )
    previous = state.assignee_id
    state.assignee_id = person.id
    await notify_assignment(
        db,
        assignee_id=person.id,
        previous_assignee_id=previous,
        role_label="assignee",
        artefact_label=artefact_public_id(artefact_identity(row)[0], row),
        project_id=row.project_id,
        link_path=await document_path(db, row),
        actor=user,
    )


@router.post(
    "/artefacts/{slug}/{identifier}/requests",
    responses={
        403: {"description": HTTPStatus(403).phrase},
        404: {"description": HTTPStatus(404).phrase},
        409: {"description": HTTPStatus(409).phrase},
    },
)
async def create_request(
    slug: str,
    identifier: str,
    data: RequestStart,
    response: Response,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    row = await visible_artefact(db, slug, identifier, user, lock=True)
    result, created = await request_handoff(db, row, user, data.kind)
    response.status_code = 201 if created else 200
    return result


@router.post(
    "/artefact-requests/{request_id}/decline",
    responses={
        403: {"description": HTTPStatus(403).phrase},
        404: {"description": HTTPStatus(404).phrase},
        409: {"description": HTTPStatus(409).phrase},
    },
)
async def decline_request(
    request_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    request = await db.get(ArtefactRequest, request_id)
    state = await db.get(ArtefactWorkflow, request.workflow_id) if request else None
    if not state:
        raise HTTPException(status_code=404, detail="Request not found")
    row = await visible_artefact(db, state.artefact_type, state.artefact_id, user, lock=True)
    if not await _delivered_actor(db, row, state, request, user):
        raise HTTPException(status_code=403, detail="This request was not delivered to you.")
    if request.status != "pending" or request.revision_number != state.revision_number:
        raise HTTPException(status_code=409, detail="This request is no longer pending.")
    with permit_workflow_write(db, row):
        request.status = "declined"
        request.decided_by_id = user.id
        request.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
        state.phase = "Draft" if request.kind == "review" else "Review"
        row.status = "Draft" if request.kind == "review" else "Review"
        await db.flush()
    await _event(db, state, user, "declined", request)
    requester = await db.get(User, request.requester_id) if request.requester_id else None
    if requester and requester.is_active:
        await _deliver(db, row, request, requester, user, "declined")
    return {"id": request.id, "status": request.status}


@router.get(
    "/projects/{project_id}/artefact-requests",
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def project_requests(
    project_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    from app.core.security import require_project_access

    await require_project_access(db, user, project_id)
    result = []
    for request, state in (
        await db.execute(
            select(ArtefactRequest, ArtefactWorkflow)
            .join(ArtefactWorkflow, ArtefactWorkflow.id == ArtefactRequest.workflow_id)
            .where(ArtefactWorkflow.project_id == project_id, ArtefactRequest.status == "pending")
            .order_by(ArtefactRequest.created_at.desc())
        )
    ).all():
        try:
            row = await visible_artefact(db, state.artefact_type, state.artefact_id, user)
        except HTTPException:
            continue
        step = "review" if request.kind == "review" else "approve"
        if request.requester_id == user.id or (
            await db.get(ArtefactRequestRecipient, (request.id, user.id))
            and await _may_sign(db, user, row, step)
        ):
            result.append(
                {
                    "id": request.id,
                    "kind": request.kind,
                    "status": request.status,
                    "artefact_type": state.artefact_type,
                    "artefact_id": state.artefact_id,
                    "doc_type": artefact_identity(row)[1],
                    "public_id": artefact_public_id(state.artefact_type, row),
                    "revision_number": request.revision_number,
                    "created_at": _time(request.created_at),
                }
            )
    return result


@router.post(
    "/artefacts/{slug}/{identifier}/draft",
    responses={
        404: {"description": HTTPStatus(404).phrase},
        409: {"description": HTTPStatus(409).phrase},
    },
)
async def start_legacy_draft(
    slug: str,
    identifier: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    row = await visible_artefact(db, slug, identifier, user, "edit", lock=True)
    state = await get_workflow(db, row, initial_phase="Draft")
    if (
        not controlled(row)
        or row.status == "Approved"
        or state.phase == "Approved"
        or (state.revision_creator_id is not None and row.status in {"Draft", "Review"})
    ):
        raise HTTPException(status_code=409, detail="This document does not need a legacy Draft.")
    with permit_workflow_write(db, row):
        row.status = state.phase = "Draft"
        state.revision_creator_id = user.id
        await db.flush()
    await _event(db, state, user, "draft_started")
    return await workflow_response(db, row, user)


@router.post(
    "/artefacts/{slug}/{identifier}/revisions",
    status_code=201,
    responses={
        404: {"description": HTTPStatus(404).phrase},
        409: {"description": HTTPStatus(409).phrase},
    },
)
async def start_revision(
    slug: str,
    identifier: str,
    data: RevisionStart,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    await visible_artefact(db, slug, identifier, user, "edit", lock=True)
    raise HTTPException(
        status_code=409,
        detail="Edit and save the document; revision changes use its linked approved CHG.",
    )


async def _revision_visible(db, row, revision, user):
    """Check the archived origin and tags independently of current visibility."""
    snapshot = revision.content_snapshot
    archived = type(row)(project_id=row.project_id, id=row.id)
    for field in ("doc_type", "visibility", "req_origin"):
        if field in snapshot["fields"]:
            setattr(archived, field, snapshot["fields"][field])
    return await covers_with_tags(db, user, archived, "view", snapshot.get("tag_ids", []))


async def _visible_revision(db, slug, identifier, number, user):
    """Resolve an immutable revision only through its visible current parent."""
    row = await visible_artefact(db, slug, identifier, user)
    state = await get_workflow(db, row, create=False)
    revision = (
        await db.scalar(
            select(ArtefactRevision).where(
                ArtefactRevision.workflow_id == state.id, ArtefactRevision.revision_number == number
            )
        )
        if state
        else None
    )
    if not revision or not await _revision_visible(db, row, revision, user):
        raise HTTPException(status_code=404, detail="Revision not found")
    return row, revision


@router.get(
    "/artefacts/{slug}/{identifier}/revisions/{number}",
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def read_revision(
    slug: str,
    identifier: str,
    number: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    _, revision = await _visible_revision(db, slug, identifier, number, user)
    snapshot = {
        key: value
        for key, value in revision.content_snapshot.items()
        if key in {"fields", "sections", "suite_items", "signoffs", "signoff_identities"}
    }
    files = (
        await db.scalars(
            select(ArtefactRevisionFile).where(ArtefactRevisionFile.revision_id == revision.id)
        )
    ).all()
    snapshot["attachments"] = [
        {
            "id": file.id,
            "original_filename": file.original_filename,
            "content_type": file.content_type,
            "file_size": file.size_bytes,
        }
        for file in files
    ]
    items = []
    for item in snapshot.get("suite_items", []):
        case = await db.get(TestCase, item["test_case_id"])
        if case and await row_allows(db, user, case, "view", "TC"):
            items.append({**item, "test_case": {"tc_id": case.tc_id, "title": case.title}})
    snapshot["suite_items"] = items
    sections = []
    for section in snapshot.get("sections", []):
        item = dict(section)
        linked = item.get("linked_requirement_id")
        requirement = await db.get(Requirement, linked) if linked else None
        if linked and (
            not requirement or not await row_allows(db, user, requirement, "view", "REQ")
        ):
            item["linked_requirement_id"] = None
        sections.append(item)
    snapshot["sections"] = sections
    return {
        "revision_number": revision.revision_number,
        "approved_by": await _person(db, revision.approved_by_id),
        "approved_at": _time(revision.approved_at),
        "authorizing_change": await _change(db, revision.authorizing_change_id, user),
        "snapshot": snapshot,
    }


@router.get(
    "/artefacts/{slug}/{identifier}/revisions/{number}/attachments/{file_id}",
    responses={
        404: {"description": HTTPStatus(404).phrase},
        503: {"description": HTTPStatus(503).phrase},
    },
)
async def revision_file(
    slug: str,
    identifier: str,
    number: int,
    file_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    user: User = Depends(get_current_user),
):
    _, revision = await _visible_revision(db, slug, identifier, number, user)
    file = await db.get(ArtefactRevisionFile, file_id)
    if not file or file.revision_id != revision.id:
        raise HTTPException(status_code=404, detail="Revision file not found")
    name = attachment_storage.safe_display_name(file.original_filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}",
        "X-Content-Type-Options": "nosniff",
    }
    if object_store.s3_enabled():
        try:
            body = await object_store.fetch(file.storage_path)
            return StreamingResponse(
                object_store.iter_body(body), media_type=file.content_type, headers=headers
            )
        except Exception:
            if not object_store.keeps_local_copy():
                raise HTTPException(status_code=503, detail="The file store is unreachable.")
    path = attachment_storage.resolve_stored_path(file.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Revision file not found")
    return FileResponse(path, media_type=file.content_type, headers=headers)


async def _deliver(db, row, request, recipient, actor, outcome=None):
    """Notify and email only a recipient that can currently read the document."""
    if not await row_allows(db, recipient, row, "view"):
        return False
    public_id = artefact_public_id(artefact_identity(row)[0], row)
    path = await document_path(db, row)
    title = (
        f"{request.kind.capitalize()} {'requested' if outcome is None else outcome}: {public_id}"
    )
    text = f"{actor.full_name}: {title}\n{settings.APP_BASE_URL.rstrip('/')}{path}"
    await notify(
        db,
        user_id=recipient.id,
        event_type="workflow",
        title=title,
        body=text,
        link_path=path,
        project_id=row.project_id,
        actor=actor,
    )
    try:
        send_workflow_request_email(
            to_email=recipient.email,
            recipient_name=recipient.full_name,
            actor_name=actor.full_name,
            event_title=title,
            document_link=f"{settings.APP_BASE_URL.rstrip('/')}{path}",
        )
        return True
    except MailConfigurationError:
        return False
