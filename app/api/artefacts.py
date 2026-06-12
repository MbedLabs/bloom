"""Generic artefact comments, activity, workflow, and related endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    artefact_public_id,
    build_activity_response,
    build_related_response,
    get_allowed_transitions,
    get_artefact_or_404,
    log_artefact_activity,
    log_workflow_status_transition,
)
from app.core.database import get_db
from app.core.security import get_current_user, require_project_access, require_role
from app.models import ArtefactActivity, ArtefactComment
from app.models.user import User, UserRole
from app.schemas import (
    ArtefactActivityResponse,
    ArtefactCommentCreate,
    ArtefactCommentResponse,
    ArtefactRelatedResponse,
    ArtefactTransitionRequest,
)

router = APIRouter()


@router.get(
    "/{artefact_type}/{artefact_id}/comments",
    response_model=list[ArtefactCommentResponse],
)
async def list_comments(
    artefact_type: str,
    artefact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    artefact = await get_artefact_or_404(db, artefact_type, artefact_id, current_user)
    await require_project_access(db, current_user, artefact.project_id)
    comments = (
        (
            await db.execute(
                select(ArtefactComment)
                .where(
                    ArtefactComment.artefact_type == artefact_type,
                    ArtefactComment.artefact_id == artefact_id,
                )
                .order_by(ArtefactComment.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [ArtefactCommentResponse.model_validate(comment) for comment in comments]


@router.post(
    "/{artefact_type}/{artefact_id}/comments",
    response_model=ArtefactCommentResponse,
    status_code=201,
)
async def create_comment(
    artefact_type: str,
    artefact_id: int,
    data: ArtefactCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    artefact = await get_artefact_or_404(db, artefact_type, artefact_id, current_user)
    await require_project_access(db, current_user, artefact.project_id)
    comment = ArtefactComment(
        artefact_type=artefact_type,
        artefact_id=artefact_id,
        author_name=current_user.full_name,
        body=data.body,
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
    return ArtefactCommentResponse.model_validate(comment)


@router.get(
    "/{artefact_type}/{artefact_id}/activity",
    response_model=list[ArtefactActivityResponse],
)
async def list_activity(
    artefact_type: str,
    artefact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    artefact = await get_artefact_or_404(db, artefact_type, artefact_id, current_user)
    await require_project_access(db, current_user, artefact.project_id)
    rows = (
        (
            await db.execute(
                select(ArtefactActivity)
                .where(
                    ArtefactActivity.artefact_type == artefact_type,
                    ArtefactActivity.artefact_id == artefact_id,
                )
                .order_by(ArtefactActivity.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [build_activity_response(row) for row in rows]


@router.get("/{artefact_type}/{artefact_id}/related", response_model=ArtefactRelatedResponse)
async def get_related_items(
    artefact_type: str,
    artefact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    artefact = await get_artefact_or_404(db, artefact_type, artefact_id, current_user)
    await require_project_access(db, current_user, artefact.project_id)
    return await build_related_response(db, artefact_type, artefact_id, current_user)


@router.post("/{artefact_type}/{artefact_id}/transition")
async def transition_status(
    artefact_type: str,
    artefact_id: int,
    data: ArtefactTransitionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    artefact = await get_artefact_or_404(db, artefact_type, artefact_id, current_user)
    await require_project_access(
        db,
        current_user,
        artefact.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )
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
