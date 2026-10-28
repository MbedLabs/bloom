"""Record audit events: who did what, from where, and with what outcome.

The acting user, the request id, the client address and the user agent come from
the request context; a call site names the action and its target. Every HTTP request
also leaves one api.request event, and repeated refusals from one address leave a
security.repeated_refusals event.
"""

from __future__ import annotations

import hashlib
import inspect
import logging
import re
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import parse_qsl

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability import (
    client_ip_var,
    request_audit_var,
    request_id_var,
    user_agent_var,
)
from app.models.audit import AuditEvent

logger = logging.getLogger(__name__)

audit_actor_var: ContextVar[Optional[tuple[str, Optional[int]]]] = ContextVar(
    "audit_actor", default=None
)

SECRET_KEYS = frozenset(
    {"password", "token", "secret", "api_key", "hashed_password", "credential", "webhook_secret"}
)
NAMED_KEYS = frozenset({"service_credential_id"})

REQUEST_ACTION = "api.request"
REPEATED_REFUSALS_ACTION = "security.repeated_refusals"
DENIED_STATUSES = frozenset({401, 403, 429})
DOCUMENT_ID_KEYS = (
    "doc_id",
    "req_id",
    "tc_id",
    "design_id",
    "risk_id",
    "change_id",
    "concept_id",
    "defect_id",
    "campaign_id",
    "suite_id",
    "baseline_id",
)
PATH_PARAM = re.compile(r"\{([^}:]+)(?::[^}]*)?\}")
MAX_PATH_LENGTH = 1000
MAX_QUERY_NAMES = 50
MAX_QUERY_NAME_LENGTH = 100


def set_audit_actor(
    actor_type: str,
    actor_user_id: Optional[int] = None,
    *,
    client: Optional[str] = None,
    service_credential_id: Optional[int] = None,
) -> None:
    """Remember who acts in the current request, with the client kind of a user token (cli or
    web) and the id of a service credential, for the request's events and its api.request
    event."""
    audit_actor_var.set((actor_type, actor_user_id))
    request = request_audit_var.get()
    if request is not None:
        request.actor_type = actor_type
        request.actor_user_id = actor_user_id
        request.client = client
        request.service_credential_id = service_credential_id


def mark_refused() -> None:
    """Mark the current request as a refusal: its 404 hides something its actor may not see
    and its api.request event is denied."""
    request = request_audit_var.get()
    if request is not None:
        request.refused = True


def _clean(details: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Drop every key that names a secret, at any depth; NAMED_KEYS hold ids and stay."""
    if details is None:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in details.items():
        if key not in NAMED_KEYS and any(part in key.lower() for part in SECRET_KEYS):
            continue
        cleaned[key] = _clean(value) if isinstance(value, dict) else value
    return cleaned


def build_audit_event(
    action: str,
    *,
    target_type: Optional[str] = None,
    target_id: Any = None,
    project_id: Optional[int] = None,
    outcome: str = "success",
    details: Optional[dict[str, Any]] = None,
    actor_user_id: Optional[int] = None,
    actor_type: Optional[str] = None,
) -> AuditEvent:
    """Build an audit row from the arguments and the request context."""
    context_actor = audit_actor_var.get()
    if actor_type is None:
        if actor_user_id is not None:
            actor_type = "user"
        elif context_actor is not None:
            actor_type, actor_user_id = context_actor
        else:
            actor_type = "anonymous"
    request_id = request_id_var.get()
    user_agent = user_agent_var.get()
    return AuditEvent(
        actor_user_id=actor_user_id,
        actor_type=actor_type,
        action=action,
        target_type=target_type,
        target_id=None if target_id is None else str(target_id),
        project_id=project_id,
        request_id=None if request_id == "-" else request_id,
        ip=client_ip_var.get(),
        user_agent=user_agent[:255] if user_agent else None,
        outcome=outcome,
        details=_clean(details),
    )


async def record_audit_event(db: AsyncSession, action: str, **fields: Any) -> None:
    """Add an audit row to the request's transaction, committed with the action."""
    db.add(build_audit_event(action, **fields))
    await db.flush()


async def record_audit_failure(db: AsyncSession, action: str, **fields: Any) -> None:
    """Commit a failure audit row on its own session, so the request's rollback keeps it.

    A failure to write the row is logged and never changes the request's answer.
    """
    fields.setdefault("outcome", "failure")
    try:
        async with AsyncSession(bind=db.bind) as session:
            session.add(build_audit_event(action, **fields))
            await session.commit()
    except SQLAlchemyError:
        logger.exception("Audit event %s could not be recorded", action)


def request_outcome(status_code: int, refused: bool = False, anonymous: bool = False) -> str:
    """success below 400; denied for 401, 403, 429, a 404 that hid something and a 404 to an
    anonymous caller; else failure."""
    if status_code in DENIED_STATUSES or (status_code == 404 and (refused or anonymous)):
        return "denied"
    if status_code >= 400:
        return "failure"
    return "success"


def route_template(scope: dict) -> str:
    """The full route template of the matched route, prefixes included, or "unmatched"."""
    route = scope.get("route")
    template = getattr(route, "path_format", getattr(route, "path", None))
    if route is None or template is None:
        return "unmatched"
    path = scope.get("path", "")
    pattern = getattr(route, "path_regex", None)
    if pattern is not None:
        starts = [index for index, char in enumerate(path) if char == "/"] + [len(path)]
        for start in starts:
            if pattern.match(path[start:]):
                return path[:start] + template
    return template


def _target(template: str, params: dict) -> tuple[Optional[str], Optional[str]]:
    """The target named by the last path parameter ending in _id."""
    names = [name for name in PATH_PARAM.findall(template) if name.endswith("_id")]
    for name in reversed(names):
        if name in params:
            return name[: -len("_id")][:50], str(params[name])[:100]
    return None, None


def _project_id(params: dict) -> Optional[int]:
    """The project_id path parameter as a number, when the route has one."""
    value = str(params.get("project_id", ""))
    return int(value) if value.isdigit() else None


def _query_names(scope: dict) -> list[str]:
    """The distinct query parameter names, without their values."""
    query = scope.get("query_string", b"").decode("latin-1")
    names: list[str] = []
    for name, _value in parse_qsl(query, keep_blank_values=True):
        name = name[:MAX_QUERY_NAME_LENGTH]
        if name not in names:
            names.append(name)
        if len(names) >= MAX_QUERY_NAMES:
            break
    return names


def _created(body: Any) -> dict[str, Any]:
    """The id (id, else document_id) and the document ID of a created object's JSON body."""
    if not isinstance(body, dict):
        return {}
    created_id = body.get("id", body.get("document_id"))
    if created_id is None:
        return {}
    created: dict[str, Any] = {"created_id": created_id}
    for key in DOCUMENT_ID_KEYS:
        value = body.get(key)
        if isinstance(value, str) and value:
            created["created_doc_id"] = value
            break
    return created


async def _open_session(scope: dict):
    """A session from the application's database dependency, with its closer."""
    from app.core.database import get_db

    app = scope.get("app")
    overrides = getattr(app, "dependency_overrides", None) or {}
    provider = overrides.get(get_db, get_db)
    produced = provider()
    if inspect.isasyncgen(produced):
        return await produced.__anext__(), produced.aclose
    session = await produced

    async def _close():
        await session.close()

    return session, _close


def refusal_lock_key(ip: str) -> int:
    """The signed 64-bit advisory lock key of an address's repeated refusal check."""
    digest = hashlib.sha256(f"{REPEATED_REFUSALS_ACTION}:{ip}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


async def _note_repeated_refusals(session: AsyncSession, ip: str, actor: dict) -> None:
    """Add one security.repeated_refusals event when the address reached the threshold of
    denied requests within the window and has none inside the window yet; on PostgreSQL the
    check and the insert hold a transaction-scoped advisory lock on the address."""
    from app.core.config import settings

    window = settings.AUDIT_REFUSAL_WINDOW_MINUTES
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=window)
    count = await session.scalar(
        select(func.count(AuditEvent.id)).where(
            AuditEvent.action == REQUEST_ACTION,
            AuditEvent.outcome == "denied",
            AuditEvent.ip == ip,
            AuditEvent.occurred_at >= since,
        )
    )
    if (count or 0) < settings.AUDIT_REFUSAL_THRESHOLD:
        return
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": refusal_lock_key(ip)}
        )
    already = await session.scalar(
        select(AuditEvent.id)
        .where(
            AuditEvent.action == REPEATED_REFUSALS_ACTION,
            AuditEvent.ip == ip,
            AuditEvent.occurred_at >= since,
        )
        .limit(1)
    )
    if already is not None:
        await session.rollback()
        return
    session.add(
        build_audit_event(
            REPEATED_REFUSALS_ACTION,
            outcome="denied",
            details={"address": ip, "count": count, "window_minutes": window},
            **actor,
        )
    )
    await session.commit()


async def record_request_event(
    scope: dict,
    *,
    authorization: str,
    status_code: int,
    duration_ms: float,
    created_body: Any = None,
) -> None:
    """Commit the request's api.request event on its own session, then check the address
    for repeated refusals when the request was denied.

    The details hold the method, route template, path, status, duration, query parameter
    names, the credential kind presented (bearer or none), the client kind of a user token,
    the service credential id and the id and document ID of a created object; never a body,
    header or query value.
    """
    request = request_audit_var.get()
    template = route_template(scope)
    params = scope.get("path_params") or {}
    target_type, target_id = _target(template, params)
    details: dict[str, Any] = {
        "method": scope.get("method", "-"),
        "route": template,
        "path": scope.get("path", "")[:MAX_PATH_LENGTH],
        "status": status_code,
        "duration_ms": duration_ms,
        "query": _query_names(scope),
        "auth": "bearer" if authorization.lower().startswith("bearer ") else "none",
    }
    actor: dict[str, Any] = {"actor_type": "anonymous", "actor_user_id": None}
    refused = False
    if request is not None:
        refused = request.refused
        if request.actor_type is not None:
            actor = {"actor_type": request.actor_type, "actor_user_id": request.actor_user_id}
        if request.client is not None:
            details["client"] = request.client
        if request.service_credential_id is not None:
            details["service_credential_id"] = request.service_credential_id
    if status_code == 201:
        details.update(_created(created_body))
    outcome = request_outcome(status_code, refused, actor["actor_type"] == "anonymous")
    event = build_audit_event(
        REQUEST_ACTION,
        target_type=target_type,
        target_id=target_id,
        project_id=_project_id(params),
        outcome=outcome,
        details=details,
        **actor,
    )
    session, close = await _open_session(scope)
    try:
        session.add(event)
        await session.commit()
        if outcome == "denied" and event.ip:
            await _note_repeated_refusals(session, event.ip, actor)
    finally:
        await close()
