"""Audit log API (admin only): read the audit events, newest first, with filters.

There is no endpoint that changes or deletes an event.
"""

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, case, cast, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.models.audit import AuditEvent
from app.models.user import User, UserRole
from app.schemas.audit import AuditEventPage, AuditEventResponse

router = APIRouter()

require_admin = require_role(UserRole.admin)


@router.get("", response_model=AuditEventPage)
async def list_audit_events(
    actor_user_id: Optional[int] = None,
    actor_type: Optional[str] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    project_id: Optional[int] = None,
    outcome: Optional[str] = None,
    ip: Optional[str] = None,
    request_id: Optional[str] = None,
    status: Optional[int] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Literal[
        "occurred_at", "actor", "action", "target", "outcome", "ip", "request_id"
    ] = "occurred_at",
    dir: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db, scope="function"),
    _admin: User = Depends(require_admin),
):
    """List audit events matching every given filter; an action filter ending in "." is a prefix
    and status matches details.status, the HTTP status of an api.request event."""
    conditions = []
    if actor_user_id is not None:
        conditions.append(AuditEvent.actor_user_id == actor_user_id)
    if actor_type:
        conditions.append(AuditEvent.actor_type == actor_type)
    if action:
        if action.endswith("."):
            conditions.append(AuditEvent.action.startswith(action))
        else:
            conditions.append(AuditEvent.action == action)
    if target_type:
        conditions.append(AuditEvent.target_type == target_type)
    if target_id:
        conditions.append(AuditEvent.target_id == target_id)
    if project_id is not None:
        conditions.append(AuditEvent.project_id == project_id)
    if outcome:
        conditions.append(AuditEvent.outcome == outcome)
    if ip:
        conditions.append(AuditEvent.ip == ip)
    if request_id:
        conditions.append(AuditEvent.request_id == request_id)
    if status is not None:
        conditions.append(cast(AuditEvent.details["status"].as_string(), String) == str(status))
    if since is not None:
        conditions.append(AuditEvent.occurred_at >= since)
    if until is not None:
        conditions.append(AuditEvent.occurred_at < until)

    sort_columns = {
        "occurred_at": AuditEvent.occurred_at,
        "actor": func.coalesce(
            User.full_name,
            case(
                (
                    AuditEvent.actor_user_id.is_not(None),
                    literal("User ") + cast(AuditEvent.actor_user_id, String),
                ),
                else_=AuditEvent.actor_type,
            ),
        ),
        "action": AuditEvent.action,
        "target": func.coalesce(AuditEvent.target_type, "")
        + literal(" ")
        + func.coalesce(AuditEvent.target_id, ""),
        "outcome": AuditEvent.outcome,
        "ip": func.coalesce(AuditEvent.ip, ""),
        "request_id": func.coalesce(AuditEvent.request_id, ""),
    }
    column = sort_columns[sort]
    ordering = column.asc() if dir == "asc" else column.desc()
    tie_breaker = AuditEvent.id.asc() if dir == "asc" else AuditEvent.id.desc()
    total = await db.scalar(select(func.count(AuditEvent.id)).where(*conditions))
    rows = (
        await db.execute(
            select(AuditEvent, User)
            .outerjoin(User, User.id == AuditEvent.actor_user_id)
            .where(*conditions)
            .order_by(ordering, tie_breaker)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    items = []
    for event, actor in rows:
        item = AuditEventResponse.model_validate(event)
        item.actor_name = actor.full_name if actor else None
        item.actor_profile_picture_url = actor.profile_picture_url if actor else None
        items.append(item)
    return AuditEventPage(items=items, total=total or 0)
