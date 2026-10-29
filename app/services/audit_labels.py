"""Human labels for the actors and targets of audit events.

A target is named by its project prefix, document ID, name or email; a missing object keeps
its number, marked deleted. Stored events are not changed.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import ARTEFACT_PUBLIC_ID_ATTRS
from app.models import (
    Baseline,
    Group,
    Policy,
    Project,
    ServiceCredential,
    Tag,
)
from app.models.access_request import AccessRequest
from app.models.audit import AuditEvent
from app.models.tags import TAGGED_MODELS, TYPE_CODES
from app.models.user import User
from app.models.workflow import ArtefactRequest, ArtefactWorkflow

TARGET_ALIASES = {
    "test_case": "test-case",
    "test_concept": "test-concept",
    "concept": "test-concept",
    "suite": "test-suite",
    "test_suite": "test-suite",
    **{code: slug for slug, code in TYPE_CODES.items() if code},
}

NAMED_TARGETS: dict[str, tuple[Any, str]] = {
    "project": (Project, "prefix"),
    "group": (Group, "name"),
    "policy": (Policy, "name"),
    "tag": (Tag, "name"),
    "baseline": (Baseline, "baseline_id"),
    "service_credential": (ServiceCredential, "name"),
}


def _route_params(route: Any, path: Any) -> dict[str, str]:
    """The path parameters of an API request, read by aligning its route template and path."""
    if not isinstance(route, str) or not isinstance(path, str):
        return {}
    template_parts = route.strip("/").split("/")
    path_parts = path.strip("/").split("/")
    if len(template_parts) != len(path_parts):
        return {}
    return {
        part[1:-1].split(":")[0]: value
        for part, value in zip(template_parts, path_parts)
        if part.startswith("{") and part.endswith("}")
    }


def _kind(event: AuditEvent) -> Optional[str]:
    """The labelled kind of an event's target: a document slug, a named type, user, or the
    access or workflow request an API request names."""
    target_type = event.target_type
    if not target_type:
        return None
    details = event.details or {}
    if target_type == "artefact":
        slug = _route_params(details.get("route"), details.get("path")).get("artefact_type")
        return slug if slug in TAGGED_MODELS else None
    if target_type == "request":
        route = str(details.get("route", ""))
        if "/access-requests/" in route:
            return "access_request"
        if "/artefact-requests/" in route:
            return "artefact_request"
        return None
    return TARGET_ALIASES.get(target_type, target_type)


def _words(target_type: str) -> str:
    """A target type as words."""
    return target_type.replace("_", " ").replace("-", " ")


async def _rows(db: AsyncSession, model: Any, ids: Iterable[int]) -> dict[int, Any]:
    """The rows of a model with the given ids, by id."""
    wanted = sorted(set(ids))
    if not wanted:
        return {}
    return {row.id: row for row in (await db.scalars(select(model).where(model.id.in_(wanted))))}


def _public_id(slug: str, row: Any) -> str:
    """The document ID of an item, or its database id when it has none."""
    value = getattr(row, ARTEFACT_PUBLIC_ID_ATTRS.get(slug, "id"), None)
    return str(value if value is not None else row.id)


def _user_name(user: User) -> str:
    """A user's name, else their email."""
    return user.full_name or user.email


async def target_labels(db: AsyncSession, events: list[AuditEvent]) -> dict[int, str]:
    """The target label of each event that has a target, by event id."""
    wanted: dict[str, list[int]] = defaultdict(list)
    kinds: dict[int, Optional[str]] = {}
    for event in events:
        kind = _kind(event)
        kinds[event.id] = kind
        if kind and event.target_id and event.target_id.isdigit():
            wanted[kind].append(int(event.target_id))

    found: dict[str, dict[int, str]] = {}
    for kind, ids in wanted.items():
        if kind in TAGGED_MODELS:
            found[kind] = {
                key: _public_id(kind, row)
                for key, row in (await _rows(db, TAGGED_MODELS[kind], ids)).items()
            }
        elif kind in NAMED_TARGETS:
            model, attr = NAMED_TARGETS[kind]
            found[kind] = {
                key: str(getattr(row, attr, None) or getattr(row, "name", None) or key)
                for key, row in (await _rows(db, model, ids)).items()
            }
        elif kind == "user":
            found[kind] = {
                key: _user_name(row) for key, row in (await _rows(db, User, ids)).items()
            }
        elif kind == "access_request":
            found[kind] = {
                key: f"{_words(row.resource_type)} {row.resource_ref}"
                + (f" in project {row.project_prefix}" if row.project_prefix else "")
                for key, row in (await _rows(db, AccessRequest, ids)).items()
            }
        elif kind == "artefact_request":
            requests = await _rows(db, ArtefactRequest, ids)
            workflows = await _rows(
                db, ArtefactWorkflow, (r.workflow_id for r in requests.values())
            )
            by_slug: dict[str, list[int]] = defaultdict(list)
            for workflow in workflows.values():
                by_slug[workflow.artefact_type].append(workflow.artefact_id)
            items = {
                slug: await _rows(db, TAGGED_MODELS[slug], item_ids)
                for slug, item_ids in by_slug.items()
                if slug in TAGGED_MODELS
            }
            labels = {}
            for key, request in requests.items():
                workflow = workflows.get(request.workflow_id)
                item = (
                    items.get(workflow.artefact_type, {}).get(workflow.artefact_id)
                    if workflow
                    else None
                )
                if item is not None:
                    labels[key] = f"{request.kind} of {_public_id(workflow.artefact_type, item)}"
            found[kind] = labels

    labels: dict[int, str] = {}
    for event in events:
        if not event.target_type:
            continue
        kind = kinds[event.id]
        target_id = event.target_id or ""
        shown_type = _words(
            kind
            if kind and kind not in {"access_request", "artefact_request"}
            else event.target_type
        )
        if kind is None or kind not in found or not target_id.isdigit():
            labels[event.id] = f"{shown_type} {target_id}".strip()
            continue
        human = found[kind].get(int(target_id))
        labels[event.id] = (
            f"{shown_type} {human}" if human is not None else f"{shown_type} {target_id} (deleted)"
        )
    return labels


async def actor_labels(
    db: AsyncSession, events: list[AuditEvent], users: dict[int, User]
) -> dict[int, str]:
    """The actor label of each event with a user or service credential actor, by event id."""
    credential_ids = {
        int(value)
        for event in events
        if event.actor_type == "service"
        and str(value := (event.details or {}).get("service_credential_id", "")).isdigit()
    }
    credentials = await _rows(db, ServiceCredential, credential_ids)
    labels: dict[int, str] = {}
    for event in events:
        if event.actor_user_id is not None:
            user = users.get(event.actor_user_id)
            labels[event.id] = _user_name(user) if user else f"User {event.actor_user_id} (deleted)"
            continue
        raw = str((event.details or {}).get("service_credential_id", ""))
        if event.actor_type == "service" and raw.isdigit():
            credential = credentials.get(int(raw))
            labels[event.id] = (
                credential.name if credential else f"Service credential #{raw} (deleted)"
            )
    return labels
