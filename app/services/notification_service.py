"""Creating in-app notifications."""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification
from app.models.user import User

logger = logging.getLogger(__name__)


async def notify(
    db: AsyncSession,
    *,
    user_id: int,
    event_type: str,
    title: str,
    project_id: Optional[int] = None,
    body: Optional[str] = None,
    link_path: Optional[str] = None,
    actor: Optional[User] = None,
) -> Optional[Notification]:
    """Create one notification. Self-notifications (actor == recipient) are skipped.

    Never raises: notification failures must not break the write they decorate.
    """
    if actor is not None and actor.id == user_id:
        return None
    try:
        notification = Notification(
            user_id=user_id,
            project_id=project_id,
            event_type=event_type,
            title=title[:500],
            body=body,
            link_path=link_path[:500] if link_path else None,
        )
        db.add(notification)
        await db.flush()
        return notification
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to create notification for user %s", user_id)
        return None


async def notify_assignment(
    db: AsyncSession,
    *,
    assignee_id: Optional[int],
    previous_assignee_id: Optional[int],
    role_label: str,
    artefact_label: str,
    project_id: Optional[int],
    link_path: Optional[str],
    actor: User,
) -> None:
    """Notify a newly assigned reviewer/approver (only when the assignee changed)."""
    if not assignee_id or assignee_id == previous_assignee_id:
        return
    await notify(
        db,
        user_id=assignee_id,
        event_type="assignment",
        title=f"You were assigned as {role_label} of {artefact_label}",
        body=f"{actor.full_name} assigned you as {role_label}.",
        project_id=project_id,
        link_path=link_path,
        actor=actor,
    )
