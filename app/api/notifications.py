"""Endpoints for the current user's in-app notifications."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_serializer
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Notification
from app.models.user import User

router = APIRouter()


class NotificationResponse(BaseModel):
    id: int
    event_type: str
    title: str
    body: Optional[str] = None
    actor_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_profile_picture_url: Optional[str] = None
    link_path: Optional[str] = None
    project_id: Optional[int] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    @field_serializer("read_at", "created_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None

    class Config:
        from_attributes = True


def notification_response(row: Notification, actor: Optional[User] = None) -> NotificationResponse:
    """Return the notification with its identified actor's current picture."""
    result = NotificationResponse.model_validate(row)
    result.actor_name = actor.full_name if actor else None
    result.actor_profile_picture_url = actor.profile_picture_url if actor else None
    return result


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread: int


class UnreadCountResponse(BaseModel):
    unread: int


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    base = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        base = base.where(Notification.read_at.is_(None))

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    unread = (
        await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        )
    ).scalar_one()
    rows = (
        (
            await db.execute(
                base.order_by(Notification.created_at.desc(), Notification.id.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    ids = {row.actor_user_id for row in rows if row.actor_user_id is not None}
    actors = (
        {user.id: user for user in (await db.scalars(select(User).where(User.id.in_(ids)))).all()}
        if ids
        else {}
    )
    return NotificationListResponse(
        items=[notification_response(n, actors.get(n.actor_user_id)) for n in rows],
        total=total,
        unread=unread,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    unread = (
        await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        )
    ).scalar_one()
    return UnreadCountResponse(unread=unread)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    responses={404: {"description": "Not Found"}},
)
async def mark_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    notification = (
        await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.flush()
    actor = await db.get(User, notification.actor_user_id) if notification.actor_user_id else None
    return notification_response(notification, actor)


@router.post("/read-all", response_model=UnreadCountResponse)
async def mark_all_read(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc).replace(tzinfo=None))
    )
    await db.flush()
    return UnreadCountResponse(unread=0)
