"""Audit log: one api.request row for every HTTP request, refused attempts included, one row
for every security-relevant event, written with the action it records, and one
security.repeated_refusals row when one address is refused repeatedly."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditEvent(Base):
    """Who did what, through which request, from where, and with what outcome.

    actor_type is user, service, runner or anonymous, with actor_user_id for a user. action is
    a dotted name: api.request for every HTTP request, health probes and metrics scrapes
    included, security.repeated_refusals, and the specific events (auth., user., project.,
    artefact. and the others). target_type and target_id name the object; for api.request
    the last path parameter ending in _id. project_id is the project acted in. request_id is
    the x-request-id response header, ip the client address, user_agent the client's
    User-Agent. outcome is success, failure, ignored or denied (401, 403, 429, a 404 for
    something the actor may not see and a 404 to an anonymous caller). details of an api.request hold the method, route
    template, path, status, duration_ms, query parameter names, the credential kind
    presented (bearer or none), the client kind of a user token (cli or web), the service
    credential id, and the id and document ID of a created object. No password, token,
    secret, request or response body, header value or query value is ever stored.
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_occurred_at", "occurred_at"),
        Index("ix_audit_events_actor_user_id", "actor_user_id"),
        Index("ix_audit_events_action", "action"),
        Index("ix_audit_events_target", "target_type", "target_id"),
        Index("ix_audit_events_project_id", "project_id"),
        Index("ix_audit_events_outcome", "outcome"),
        Index("ix_audit_events_ip", "ip"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    actor_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
