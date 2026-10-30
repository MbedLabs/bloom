"""Generic artefact comments, activity, workflow, and related endpoints."""

from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    ARTEFACT_LINK_TYPES,
    artefact_public_id,
    build_activity_response,
    build_related_response,
    check_external_change,
    get_allowed_transitions,
    get_artefact_or_404,
    get_visible_row,
    log_artefact_activity,
    log_workflow_status_transition,
    row_visible_to,
)
from app.api.workflow import (
    can_comment,
    comment_participants,
    complete_step,
    document_path,
    visible_artefact,
)
from app.core.database import get_db
from app.core.permissions import transition_action
from app.core.security import get_current_user
from app.models import ArtefactActivity, ArtefactComment
from app.models.user import User
from app.schemas import (
    ArtefactActivityResponse,
    ArtefactCommentCreate,
    ArtefactCommentResponse,
    ArtefactRelatedResponse,
    ArtefactSignOffRequest,
    ArtefactSignOffResponse,
    ArtefactTransitionRequest,
    CommentAnchor,
    CommentPerson,
)
from app.services.document_workflow import (
    content_hash,
    content_snapshot,
    controlled,
    get_workflow,
)
from app.services.notification_service import notify

router = APIRouter()

SIGN_OFF_TYPES = {"requirement": "REQ", "test-case": "TC"}


async def _visible_artefact(
    db: AsyncSession, artefact_type: str, artefact_id: str, current_user: User, action: str
):
    """The artefact addressed by type and id or public id, loaded through the one loader with
    the action on its type."""
    return await visible_artefact(db, artefact_type, artefact_id, current_user, action)


async def _artefact_rows(
    db: AsyncSession, model, artefact_type: str, artefact_id: str, current_user: User
) -> list:
    """The artefact's comment or activity rows, newest first, after the access check."""
    artefact = await _visible_artefact(db, artefact_type, artefact_id, current_user, "view")
    return list(
        (
            await db.execute(
                select(model)
                .where(model.artefact_type == artefact_type, model.artefact_id == artefact.id)
                .order_by(model.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


def _comment_response(comment, people, replies=()) -> ArtefactCommentResponse:
    """One comment as returned, with its author's picture, passage, resolution and replies."""
    item = ArtefactCommentResponse.model_validate(comment)
    author = people.get(comment.author_user_id)
    item.author_profile_picture_url = author.profile_picture_url if author else None
    if comment.anchor_exact:
        item.anchor = CommentAnchor(
            exact=comment.anchor_exact,
            prefix=comment.anchor_prefix or "",
            suffix=comment.anchor_suffix or "",
        )
    resolver = people.get(comment.resolved_by_id)
    if resolver:
        item.resolved_by = CommentPerson(id=resolver.id, full_name=resolver.full_name)
    item.replies = list(replies)
    return item


async def _people(db: AsyncSession, comments) -> dict:
    """The authors and resolvers of the comments, by id."""
    ids = {
        person_id
        for comment in comments
        for person_id in (comment.author_user_id, comment.resolved_by_id)
        if person_id is not None
    }
    if not ids:
        return {}
    return {
        person.id: person
        for person in (await db.scalars(select(User).where(User.id.in_(ids)))).all()
    }


@router.get(
    "/{artefact_type}/{artefact_id}/comments",
    response_model=list[ArtefactCommentResponse],
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def list_comments(
    artefact_type: str,
    artefact_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """The artefact's threads, oldest first, each with its replies oldest first."""
    comments = sorted(
        await _artefact_rows(db, ArtefactComment, artefact_type, artefact_id, current_user),
        key=lambda comment: (comment.created_at, comment.id),
    )
    people = await _people(db, comments)
    replies: dict[int, list] = {}
    for comment in comments:
        if comment.parent_id is not None:
            replies.setdefault(comment.parent_id, []).append(_comment_response(comment, people))
    return [
        _comment_response(comment, people, replies.get(comment.id, ()))
        for comment in comments
        if comment.parent_id is None
    ]


async def _thread_start(db: AsyncSession, artefact_type: str, artefact, comment_id: int):
    """The first comment of a thread on this artefact, or 422."""
    comment = await db.get(ArtefactComment, comment_id)
    if (
        comment is None
        or comment.artefact_type != artefact_type
        or comment.artefact_id != artefact.id
    ):
        raise HTTPException(status_code=422, detail="The comment is not on this document.")
    if comment.parent_id is not None:
        comment = await db.get(ArtefactComment, comment.parent_id)
    return comment


@router.post(
    "/{artefact_type}/{artefact_id}/comments",
    response_model=ArtefactCommentResponse,
    status_code=201,
    responses={
        403: {"description": HTTPStatus(403).phrase},
        404: {"description": HTTPStatus(404).phrase},
        422: {"description": HTTPStatus(422).phrase},
    },
)
async def create_comment(
    artefact_type: str,
    artefact_id: str,
    data: ArtefactCommentCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Post a comment, a reply to a thread, or a thread on a quoted passage."""
    artefact = await _visible_artefact(db, artefact_type, artefact_id, current_user, "view")
    if not await can_comment(db, current_user, artefact):
        raise HTTPException(
            status_code=403,
            detail="Only the document's creator, assignee, reviewer or approver may comment.",
        )
    thread = (
        await _thread_start(db, artefact_type, artefact, data.parent_id)
        if data.parent_id is not None
        else None
    )
    if data.anchor is not None and (thread is not None or not hasattr(artefact, "content_json")):
        raise HTTPException(
            status_code=422,
            detail="Only a new thread on a document with rich text quotes a passage.",
        )
    workflow = await get_workflow(db, artefact)
    from app.api.workflow import _review_request

    request = await _review_request(db, workflow)
    artefact_id = artefact.id
    comment = ArtefactComment(
        artefact_type=artefact_type,
        artefact_id=artefact_id,
        author_name=current_user.full_name,
        author_user_id=current_user.id,
        body=data.body,
        parent_id=thread.id if thread else None,
        anchor_exact=data.anchor.exact if data.anchor else None,
        anchor_prefix=data.anchor.prefix if data.anchor else None,
        anchor_suffix=data.anchor.suffix if data.anchor else None,
        revision_number=workflow.revision_number,
        content_hash=content_hash(await content_snapshot(db, artefact)),
        review_request_id=request.id if request and request.status == "pending" else None,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    await log_artefact_activity(
        db,
        artefact_type,
        artefact_id,
        "comment_added",
        f"{current_user.full_name} added a comment",
    )
    await _notify_comment(db, artefact, artefact_type, workflow, thread, data.body, current_user)
    return _comment_response(comment, {current_user.id: current_user})


async def _notify_comment(db, artefact, artefact_type, workflow, thread, text, current_user):
    """Notify the document's participants, and on a reply the thread's authors, who may see
    the document; the author is left out."""
    artefact_id = artefact.id
    type_code = (
        ARTEFACT_LINK_TYPES.get(artefact_type)
        or SIGN_OFF_TYPES.get(artefact_type)
        or getattr(artefact, "doc_type", None)
    )
    label = (
        getattr(artefact, "req_id", None)
        or getattr(artefact, "doc_id", None)
        or getattr(artefact, "tc_id", None)
        or getattr(artefact, "title", None)
        or f"{artefact_type} #{artefact_id}"
    )
    recipients = comment_participants(artefact, workflow)
    if thread is not None:
        recipients |= set(
            (
                await db.scalars(
                    select(ArtefactComment.author_user_id).where(
                        (ArtefactComment.id == thread.id) | (ArtefactComment.parent_id == thread.id)
                    )
                )
            ).all()
        )
    path = await document_path(db, artefact)
    for recipient_id in recipients - {current_user.id, None}:
        recipient = await db.get(User, recipient_id)
        if recipient is not None and await row_visible_to(db, recipient, artefact, type_code):
            await notify(
                db,
                user_id=recipient_id,
                event_type="comment",
                title=f"New comment on {label}",
                body=f"{current_user.full_name}: {text[:200]}",
                link_path=path,
                project_id=artefact.project_id,
                actor=current_user,
            )


async def may_resolve(db: AsyncSession, user: User, artefact) -> bool:
    """On a controlled document its creator, assignee, reviewer or approver, in any phase;
    elsewhere whoever may comment."""
    if not controlled(artefact):
        return await can_comment(db, user, artefact)
    workflow = await get_workflow(db, artefact, create=False)
    return user.is_active and user.id in comment_participants(artefact, workflow)


async def _set_resolution(artefact_type, artefact_id, comment_id, db, current_user, resolved):
    """Resolve or reopen a thread and record it in the artefact's activity."""
    artefact = await _visible_artefact(db, artefact_type, artefact_id, current_user, "view")
    if not await may_resolve(db, current_user, artefact):
        raise HTTPException(
            status_code=403,
            detail="Only the document's creator, assignee, reviewer or approver resolves threads.",
        )
    comment = await db.get(ArtefactComment, comment_id)
    if (
        comment is None
        or comment.artefact_type != artefact_type
        or comment.artefact_id != artefact.id
    ):
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.parent_id is not None:
        raise HTTPException(status_code=422, detail="Only a thread's first comment is resolved.")
    comment.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None) if resolved else None
    comment.resolved_by_id = current_user.id if resolved else None
    await db.flush()
    await log_artefact_activity(
        db,
        artefact_type,
        artefact.id,
        "comment_resolved" if resolved else "comment_reopened",
        f"{current_user.full_name} {'resolved' if resolved else 'reopened'} a thread",
    )
    replies = (
        await db.scalars(
            select(ArtefactComment)
            .where(ArtefactComment.parent_id == comment.id)
            .order_by(ArtefactComment.created_at, ArtefactComment.id)
        )
    ).all()
    people = await _people(db, [comment, *replies])
    return _comment_response(comment, people, [_comment_response(r, people) for r in replies])


@router.post(
    "/{artefact_type}/{artefact_id}/comments/{comment_id}/resolve",
    response_model=ArtefactCommentResponse,
    responses={
        403: {"description": HTTPStatus(403).phrase},
        404: {"description": HTTPStatus(404).phrase},
        422: {"description": HTTPStatus(422).phrase},
    },
)
async def resolve_comment(
    artefact_type: str,
    artefact_id: str,
    comment_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Mark a thread resolved."""
    return await _set_resolution(artefact_type, artefact_id, comment_id, db, current_user, True)


@router.post(
    "/{artefact_type}/{artefact_id}/comments/{comment_id}/reopen",
    response_model=ArtefactCommentResponse,
    responses={
        403: {"description": HTTPStatus(403).phrase},
        404: {"description": HTTPStatus(404).phrase},
        422: {"description": HTTPStatus(422).phrase},
    },
)
async def reopen_comment(
    artefact_type: str,
    artefact_id: str,
    comment_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Reopen a resolved thread."""
    return await _set_resolution(artefact_type, artefact_id, comment_id, db, current_user, False)


@router.get(
    "/{artefact_type}/{artefact_id}/activity",
    response_model=list[ArtefactActivityResponse],
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def list_activity(
    artefact_type: str,
    artefact_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    rows = await _artefact_rows(db, ArtefactActivity, artefact_type, artefact_id, current_user)
    ids = {row.actor_user_id for row in rows if row.actor_user_id is not None}
    actors = (
        {user.id: user for user in (await db.scalars(select(User).where(User.id.in_(ids)))).all()}
        if ids
        else {}
    )
    return [build_activity_response(row, actors.get(row.actor_user_id)) for row in rows]


@router.get(
    "/{artefact_type}/{artefact_id}/related",
    response_model=ArtefactRelatedResponse,
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def get_related_items(
    artefact_type: str,
    artefact_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    artefact = await _visible_artefact(db, artefact_type, artefact_id, current_user, "view")
    return await build_related_response(db, artefact_type, artefact.id, current_user)


@router.post(
    "/{artefact_type}/{artefact_id}/transition",
    responses={409: {"description": HTTPStatus(409).phrase}, 400: {"description": "Bad Request"}},
)
async def transition_status(
    artefact_type: str,
    artefact_id: str,
    data: ArtefactTransitionRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    artefact = await get_artefact_or_404(db, artefact_type, artefact_id, current_user)
    if controlled(artefact):
        raise HTTPException(status_code=409, detail="Use the document workflow for status changes.")
    resource = ARTEFACT_LINK_TYPES.get(artefact_type, artefact_type)
    artefact = await get_visible_row(
        db,
        type(artefact),
        artefact.id,
        "Artefact not found",
        current_user,
        permission=(transition_action(artefact.status, data.status), resource),
    )
    check_external_change(current_user, resource, artefact, {"status": data.status})
    artefact_id = artefact.id
    allowed = get_allowed_transitions(artefact_type, artefact.status)
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from {artefact.status} to {data.status}",
        )

    current_status = artefact.status
    artefact.status = data.status
    await db.flush()
    await log_workflow_status_transition(
        db,
        artefact_type=artefact_type,
        artefact_id=artefact_id,
        public_id=artefact_public_id(artefact_type, artefact),
        actor=current_user,
        previous_status=current_status,
        next_status=data.status,
    )
    return {
        "status": artefact.status,
        "allowed_transitions": get_allowed_transitions(artefact_type, artefact.status),
    }


@router.post(
    "/{artefact_type}/{artefact_id}/sign-off",
    response_model=ArtefactSignOffResponse,
    responses={
        403: {"description": HTTPStatus(403).phrase},
        404: {"description": HTTPStatus(404).phrase},
        409: {"description": HTTPStatus(409).phrase},
    },
)
async def sign_off(
    artefact_type: str,
    artefact_id: str,
    data: ArtefactSignOffRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Complete the current document's reviewed handoff as the authenticated actor."""
    artefact = await visible_artefact(db, artefact_type, artefact_id, current_user, lock=True)
    state = await complete_step(db, artefact, current_user, data.step)
    return ArtefactSignOffResponse(
        reviewed_by_id=state.reviewed_by_id,
        reviewed_at=state.reviewed_at,
        approved_by_id=state.approved_by_id,
        approved_at=state.approved_at,
    )
