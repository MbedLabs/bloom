"""Generic artefact comments, activity, workflow, and related endpoints."""

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
from app.api.workflow import assigned_id, can_comment, complete_step, visible_artefact
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
    comments = await _artefact_rows(db, ArtefactComment, artefact_type, artefact_id, current_user)
    ids = {comment.author_user_id for comment in comments if comment.author_user_id is not None}
    authors = (
        {
            person.id: person
            for person in (await db.scalars(select(User).where(User.id.in_(ids)))).all()
        }
        if ids
        else {}
    )
    result = []
    for comment in comments:
        item = ArtefactCommentResponse.model_validate(comment)
        author = authors.get(comment.author_user_id)
        item.author_profile_picture_url = author.profile_picture_url if author else None
        result.append(item)
    return result


@router.post(
    "/{artefact_type}/{artefact_id}/comments",
    response_model=ArtefactCommentResponse,
    status_code=201,
    responses={
        403: {"description": HTTPStatus(403).phrase},
        404: {"description": HTTPStatus(404).phrase},
    },
)
async def create_comment(
    artefact_type: str,
    artefact_id: str,
    data: ArtefactCommentCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    artefact = await _visible_artefact(db, artefact_type, artefact_id, current_user, "view")
    if not await can_comment(db, current_user, artefact):
        raise HTTPException(status_code=403, detail="Only the assigned reviewer may comment.")
    workflow = await get_workflow(db, artefact)
    from app.api.workflow import _review_request

    request = await _review_request(db, workflow)
    artefact_id = artefact.id
    type_code = (
        ARTEFACT_LINK_TYPES.get(artefact_type)
        or SIGN_OFF_TYPES.get(artefact_type)
        or getattr(artefact, "doc_type", None)
    )
    comment = ArtefactComment(
        artefact_type=artefact_type,
        artefact_id=artefact_id,
        author_name=current_user.full_name,
        author_user_id=current_user.id,
        body=data.body,
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
    label = (
        getattr(artefact, "req_id", None)
        or getattr(artefact, "doc_id", None)
        or getattr(artefact, "tc_id", None)
        or getattr(artefact, "title", None)
        or f"{artefact_type} #{artefact_id}"
    )
    for recipient_id in {
        assigned_id(artefact, workflow, "review"),
        assigned_id(artefact, workflow, "approve"),
    }:
        recipient = await db.get(User, recipient_id) if recipient_id else None
        if recipient is not None and await row_visible_to(db, recipient, artefact, type_code):
            await notify(
                db,
                user_id=recipient_id,
                event_type="comment",
                title=f"New comment on {label}",
                body=f"{current_user.full_name}: {data.body[:200]}",
                project_id=artefact.project_id,
                actor=current_user,
            )
    result = ArtefactCommentResponse.model_validate(comment)
    result.author_profile_picture_url = current_user.profile_picture_url
    return result


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
