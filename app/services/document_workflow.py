"""Capture controlled document revisions and guard authored workflow writes."""

import hashlib
import json
from contextlib import contextmanager
from datetime import datetime
from enum import Enum

from fastapi import HTTPException
from sqlalchemy import and_, inspect, or_, select
from sqlalchemy.orm import attributes

from app.core.document_kinds import normalize_document_kind
from app.core.link_rules import get_linkable_type_storage_values
from app.models.models import (
    ArtefactActivity,
    ArtefactLink,
    ChangeRequest,
    Document,
    DocumentAttachment,
    DocumentSection,
    TestSuite,
    TestSuiteItem,
)
from app.models.tags import TAG_TYPE_OF_MODEL, TAGGED_MODELS, TYPE_CODES, ArtefactTag
from app.models.user import User
from app.models.workflow import (
    ArtefactRequest,
    ArtefactRevision,
    ArtefactRevisionFile,
    ArtefactWorkflow,
)
from app.services.audit import audit_actor_var, build_audit_event

CONTROLLED_TYPES = frozenset({"REQ", "SPEC", "TC", "DES", "CPT", "PRT", "TS", "CHG"})
WORKFLOW_PHASES = ("Draft", "Review", "Approval", "Approved")
LEGACY_CHANGE_STATUSES = ("Submitted", "Closed")
SIGNOFF_FIELDS = (
    "reviewer_id",
    "approver_id",
    "reviewed_by_id",
    "reviewed_at",
    "approved_by_id",
    "approved_at",
)
NON_AUTHORING_FIELDS = frozenset(
    {
        "id",
        "project_id",
        "status",
        "created_by_id",
        "created_at",
        "updated_at",
        "source_ref",
        "source_project_id",
        "coverage",
        *SIGNOFF_FIELDS,
    }
)
IAM_FIELDS = frozenset({"visibility", "req_origin", "reviewer_id", "approver_id"})


def artefact_identity(row) -> tuple[str, str]:
    """Return the artefact route type and canonical document code."""
    slug = TAG_TYPE_OF_MODEL.get(type(row))
    if slug is None:
        raise ValueError("Unsupported artefact model")
    code = normalize_document_kind(row.doc_type) if isinstance(row, Document) else TYPE_CODES[slug]
    return slug, code


def controlled(row) -> bool:
    """Whether an artefact belongs to the controlled document lifecycle."""
    try:
        return artefact_identity(row)[1] in CONTROLLED_TYPES
    except ValueError:
        return False


def _authored_fields(row) -> set[str]:
    """The model's authoring fields excluding lifecycle and delivery metadata."""
    return {
        column.key
        for column in inspect(type(row)).columns
        if column.key not in NON_AUTHORING_FIELDS
        and not column.key.startswith(("external_", "last_"))
    }


def _json_value(value):
    """Convert recorded values into JSON-compatible snapshot data."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def recorded_phase(status: str | None) -> str | None:
    """Recognize a recorded controlled-document lifecycle phase."""
    value = str(status or "").strip().lower()
    return next((phase for phase in WORKFLOW_PHASES if phase.lower() == value), None)


async def current_status(db, row) -> str | None:
    """Read a document lifecycle phase or an exception's operational status."""
    slug, code = artefact_identity(row)
    if not controlled(row) or code == "CHG" and row.status in LEGACY_CHANGE_STATUSES:
        return row.status
    phase = await db.scalar(
        select(ArtefactWorkflow.phase).where(
            ArtefactWorkflow.artefact_type == slug,
            ArtefactWorkflow.artefact_id == row.id,
            ArtefactWorkflow.project_id == row.project_id,
        )
    )
    return phase or recorded_phase(row.status)


async def get_workflow(
    db, row, create: bool = True, *, initial_phase: str | None = None
) -> ArtefactWorkflow | None:
    """Load a cycle or initialize it from recorded status, creator and assignments."""
    slug, _ = artefact_identity(row)
    if create:
        await db.execute(select(type(row).id).where(type(row).id == row.id).with_for_update())
    workflow = (
        await db.execute(
            select(ArtefactWorkflow)
            .where(
                ArtefactWorkflow.artefact_type == slug,
                ArtefactWorkflow.artefact_id == row.id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    db.sync_session.info.setdefault("workflow_lookup_cache", {})[(slug, row.id)] = workflow
    if workflow is not None or not create:
        return workflow
    phase = initial_phase or (recorded_phase(row.status) if controlled(row) else "Draft")
    if phase not in WORKFLOW_PHASES:
        raise HTTPException(status_code=409, detail="This document has no recorded approval phase.")
    workflow = ArtefactWorkflow(
        project_id=row.project_id,
        artefact_type=slug,
        artefact_id=row.id,
        revision_number=1,
        revision_creator_id=getattr(row, "created_by_id", None),
        phase=phase,
        **{field: getattr(row, field, None) for field in SIGNOFF_FIELDS},
    )
    db.add(workflow)
    await db.flush()
    db.sync_session.info["workflow_lookup_cache"][(slug, row.id)] = workflow
    return workflow


async def content_snapshot(db, row) -> dict:
    """Record authoring fields, visibility scope, structure, files and actual signoffs."""
    slug, code = artefact_identity(row)
    tags = (
        (
            await db.execute(
                select(ArtefactTag.tag_id)
                .where(
                    ArtefactTag.artefact_type == slug,
                    ArtefactTag.artefact_id == row.id,
                    ArtefactTag.project_id == row.project_id,
                )
                .order_by(ArtefactTag.tag_id)
            )
        )
        .scalars()
        .all()
    )
    workflow = await get_workflow(db, row, create=False)
    signoffs = {
        field: _json_value(getattr(row, field, getattr(workflow, field, None)))
        for field in SIGNOFF_FIELDS
    }
    actor_ids = {
        value for key, value in signoffs.items() if key.endswith("_id") and value is not None
    }
    identities = (
        {
            str(user.id): {"id": user.id, "full_name": user.full_name}
            for user in (await db.execute(select(User).where(User.id.in_(actor_ids)))).scalars()
        }
        if actor_ids
        else {}
    )
    snapshot = {
        "artefact_type": slug,
        "type_code": code,
        "artefact_id": row.id,
        "project_id": row.project_id,
        "fields": {
            field: _json_value(getattr(row, field)) for field in sorted(_authored_fields(row))
        },
        "tag_ids": list(tags),
        "sections": [],
        "attachments": [],
        "suite_items": [],
        "signoffs": signoffs,
        "signoff_identities": identities,
        "authorizing_change_id": getattr(workflow, "authorizing_change_id", None),
    }
    if isinstance(row, Document):
        for key, model, foreign_key, order in (
            ("sections", DocumentSection, DocumentSection.document_id, DocumentSection.order),
            (
                "attachments",
                DocumentAttachment,
                DocumentAttachment.document_id,
                DocumentAttachment.id,
            ),
        ):
            rows = (
                await db.execute(
                    select(model).where(foreign_key == row.id).order_by(order, model.id)
                )
            ).scalars()
            snapshot[key] = [
                {
                    column.key: _json_value(getattr(item, column.key))
                    for column in inspect(model).columns
                }
                for item in rows
            ]
    if isinstance(row, TestSuite):
        items = (
            await db.execute(
                select(TestSuiteItem)
                .where(TestSuiteItem.suite_id == row.id)
                .order_by(TestSuiteItem.order, TestSuiteItem.id)
            )
        ).scalars()
        snapshot["suite_items"] = [
            {"id": item.id, "test_case_id": item.test_case_id, "order": item.order}
            for item in items
        ]
    return snapshot


def content_hash(snapshot: dict) -> str:
    """Hash authoring content and captured scope without status, signoffs or transport data."""
    content = {
        key: snapshot.get(key)
        for key in (
            "artefact_type",
            "type_code",
            "artefact_id",
            "project_id",
            "fields",
            "tag_ids",
            "suite_items",
        )
    }
    content["sections"] = [
        {key: value for key, value in section.items() if key not in {"created_at", "updated_at"}}
        for section in snapshot.get("sections", [])
    ]
    content["attachments"] = [
        {
            key: value
            for key, value in attachment.items()
            if key not in {"created_at", "uploaded_by_id", "source_ref", "storage_path"}
        }
        for attachment in snapshot.get("attachments", [])
    ]
    encoded = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


async def capture_revision(db, row, workflow) -> ArtefactRevision:
    """Capture approved content and retained files once for the current revision number."""
    if not controlled(row) or workflow.phase != "Approved":
        raise HTTPException(
            status_code=409, detail="Only approved controlled content can be archived."
        )
    existing = (
        await db.execute(
            select(ArtefactRevision).where(
                ArtefactRevision.workflow_id == workflow.id,
                ArtefactRevision.revision_number == workflow.revision_number,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    snapshot = await content_snapshot(db, row)
    revision = ArtefactRevision(
        workflow_id=workflow.id,
        revision_number=workflow.revision_number,
        content_snapshot=snapshot,
        content_hash=content_hash(snapshot),
        authorizing_change_id=workflow.authorizing_change_id,
        **{field: getattr(row, field, getattr(workflow, field, None)) for field in SIGNOFF_FIELDS},
    )
    db.add(revision)
    await db.flush()
    for attachment in snapshot["attachments"]:
        db.add(
            ArtefactRevisionFile(
                revision_id=revision.id,
                attachment_id=attachment["id"],
                **{
                    key: attachment.get(key)
                    for key in (
                        "filename",
                        "original_filename",
                        "content_type",
                        "size_bytes",
                        "storage_path",
                        "sha256",
                        "source_ref",
                        "uploaded_by_id",
                    )
                },
                created_at=(
                    datetime.fromisoformat(attachment["created_at"])
                    if attachment.get("created_at")
                    else None
                ),
            )
        )
    await db.flush()
    return revision


@contextmanager
def permit_workflow_write(db, row):
    """Permit an explicitly authorized workflow transition through the enclosed flush."""
    session = getattr(db, "sync_session", db)
    key = (artefact_identity(row)[0], row.id)
    permits = session.info.setdefault("workflow_write_permits", {})
    permits[key] = permits.get(key, 0) + 1
    try:
        yield
    finally:
        permits[key] -= 1
        if not permits[key]:
            permits.pop(key)


async def linked_revision_change(db, row, workflow, actor):
    """Find a new CHG in this document's existing links, excluding used authorizations."""
    from app.core.security import row_allows

    _, code = artefact_identity(row)
    kinds = get_linkable_type_storage_values(code)
    used = set(
        await db.scalars(
            select(ArtefactRevision.authorizing_change_id).where(
                ArtefactRevision.workflow_id == workflow.id
            )
        )
    )
    used.add(workflow.authorizing_change_id)
    links = (
        await db.scalars(
            select(ArtefactLink).where(
                ArtefactLink.project_id == row.project_id,
                or_(
                    and_(
                        ArtefactLink.source_type == "CHG",
                        ArtefactLink.target_type.in_(kinds),
                        ArtefactLink.target_id == row.id,
                    ),
                    and_(
                        ArtefactLink.target_type == "CHG",
                        ArtefactLink.source_type.in_(kinds),
                        ArtefactLink.source_id == row.id,
                    ),
                ),
            )
        )
    ).all()
    ids = {link.source_id if link.source_type == "CHG" else link.target_id for link in links} - used
    if not ids:
        return None
    changes = (
        await db.scalars(
            select(ChangeRequest)
            .where(ChangeRequest.id.in_(ids), ChangeRequest.project_id == row.project_id)
            .with_for_update()
        )
    ).all()
    if len(changes) != len(ids) or any(
        [not await row_allows(db, actor, change, "view", "CHG") for change in changes]
    ):
        raise HTTPException(
            status_code=409, detail="The linked CHG is not available for this change."
        )
    if any(change.status != "Approved" for change in changes):
        raise HTTPException(
            status_code=409, detail="The linked CHG must be approved before saving the change."
        )
    if len(changes) != 1:
        raise HTTPException(status_code=409, detail="Link one new approved CHG for this revision.")
    return changes[0]


async def prepare_content_write(
    db, row, actor, changes: dict | None = None
) -> ArtefactWorkflow | None:
    """Return edited content to Draft; advance its numbers only for a new linked CHG."""
    await db.refresh(row, with_for_update=True)
    if not controlled(row):
        return None
    authored_change = changes is None
    scope_change = False
    if changes is not None:
        if "status" in changes and changes["status"] != row.status:
            raise HTTPException(
                status_code=409, detail="Use the document workflow for status changes."
            )
        if isinstance(row, Document) and "version" in changes and changes["version"] != row.version:
            raise HTTPException(
                status_code=409,
                detail="Version changes only when saving a change backed by a linked approved CHG.",
            )
        authored_change = any(
            key in _authored_fields(row) - IAM_FIELDS and getattr(row, key, None) != value
            for key, value in changes.items()
        )
        scope_change = any(
            key in {"visibility", "req_origin", "tag_ids"} and getattr(row, key, None) != value
            for key, value in changes.items()
        )
        if not authored_change and not scope_change:
            return None
    workflow = await get_workflow(db, row)
    approved = str(row.status or "").strip().lower() == "approved" or workflow.phase == "Approved"
    if approved and isinstance(row, ChangeRequest) and authored_change:
        raise HTTPException(status_code=409, detail="Approved change requests cannot be edited.")
    if approved and not authored_change:
        return workflow
    archive = (
        await db.scalar(
            select(ArtefactRevision.id).where(
                ArtefactRevision.workflow_id == workflow.id,
                ArtefactRevision.revision_number == workflow.revision_number,
            )
        )
        if authored_change
        else None
    )
    change = (
        await linked_revision_change(db, row, workflow, actor)
        if authored_change and (approved or archive)
        else None
    )
    next_version = None
    if change and isinstance(row, Document):
        major = str(row.version).split(".")[0]
        if not major.isdigit():
            raise HTTPException(
                status_code=409,
                detail="The current Version must be a number before starting a CHG-backed revision.",
            )
        next_version = str(int(major) + 1)
    if approved:
        await capture_revision(db, row, workflow)
    if not approved and not change and workflow.phase not in {"Review", "Approval"}:
        return workflow
    actor_id = getattr(actor, "id", actor)
    with permit_workflow_write(db, row):
        await db.run_sync(lambda session: _invalidate_cycle(session, row, workflow, actor_id))
        if approved or change:
            workflow.revision_creator_id = actor_id
        if change:
            workflow.revision_number += 1
            workflow.authorizing_change_id = change.id
            if isinstance(row, Document):
                row.version = next_version
            db.add(
                ArtefactActivity(
                    artefact_type=workflow.artefact_type,
                    artefact_id=row.id,
                    event_type="revision_started",
                    actor_user_id=actor_id,
                    summary=f"{actor.full_name} started a new working revision",
                )
            )
            db.add(
                build_audit_event(
                    "workflow.revision_started",
                    target_type=workflow.artefact_type,
                    target_id=row.id,
                    project_id=row.project_id,
                    actor_user_id=actor_id,
                    details={
                        "revision_number": workflow.revision_number,
                        "change_request_id": change.id,
                    },
                )
            )
        await db.flush()
    return workflow


def _invalidate_cycle(session, row, workflow, actor_id) -> None:
    """Supersede pending handoffs and clear signoffs after current review content changes."""
    requests = (
        session.scalars(
            select(ArtefactRequest).where(
                ArtefactRequest.workflow_id == workflow.id,
                ArtefactRequest.revision_number == workflow.revision_number,
                ArtefactRequest.status == "pending",
            )
        ).all()
        if workflow.id is not None
        else []
    )
    now = datetime.utcnow()
    for request in requests:
        request.status = "superseded"
        request.decided_by_id = actor_id
        request.decided_at = now
    row.status = "Draft"
    workflow.phase = "Draft"
    workflow.review_content_hash = None
    for field in ("reviewed_by_id", "reviewed_at", "approved_by_id", "approved_at"):
        setattr(workflow, field, None)
        if hasattr(row, field):
            setattr(row, field, None)
    session.add(
        build_audit_event(
            "workflow.invalidated",
            target_type=workflow.artefact_type,
            target_id=row.id,
            project_id=row.project_id,
            actor_user_id=actor_id,
            details={
                "revision_number": workflow.revision_number,
                "request_ids": [request.id for request in requests],
            },
        )
    )


def _old_value(session, row, field):
    """Read a persistent column's original value before the current flush."""
    state = inspect(row)
    history = state.attrs[field].history
    if history.deleted:
        return history.deleted[0]
    if not history.has_changes() and state.attrs[field].loaded_value is not attributes.NO_VALUE:
        return state.attrs[field].loaded_value
    table = state.mapper.local_table
    return (
        session.connection()
        .execute(select(table.c[field]).where(table.c.id == state.identity[0]))
        .scalar_one_or_none()
    )


def _approved(session, row) -> bool:
    """Whether persistent content was approved before a pending edit."""
    if str(_old_value(session, row, "status") or "").strip().lower() == "approved":
        return True
    workflow = _workflow_for_write(session, row)
    phase = (
        _old_value(session, workflow, "phase")
        if workflow is not None and inspect(workflow).persistent
        else getattr(workflow, "phase", None)
    )
    return phase == "Approved"


def _workflow_for_write(session, row):
    """Reuse one live workflow lookup per artefact within the session transaction."""
    slug, _ = artefact_identity(row)
    key = (slug, row.id)
    cache = session.info.setdefault("workflow_lookup_cache", {})
    pending = next(
        (
            item
            for item in tuple(session.new) + tuple(session.identity_map.values())
            if isinstance(item, ArtefactWorkflow) and (item.artefact_type, item.artefact_id) == key
        ),
        None,
    )
    if pending is not None:
        cache[key] = pending
    if key not in cache:
        cache[key] = session.scalar(
            select(ArtefactWorkflow)
            .where(
                ArtefactWorkflow.artefact_type == slug,
                ArtefactWorkflow.artefact_id == row.id,
            )
            .with_for_update()
        )
    return cache[key]


def _child_parents(session, row):
    """Load each persistent document or suite affected by a structural write."""
    model, field = (
        (TestSuite, "suite_id") if isinstance(row, TestSuiteItem) else (Document, "document_id")
    )
    state = inspect(row)
    ids = {getattr(row, field, None), *state.attrs[field].history.deleted}
    for parent_id in ids - {None}:
        parent = session.get(model, parent_id)
        if parent is not None and inspect(parent).persistent and parent not in session.deleted:
            yield parent


def _tag_parents(session, row):
    """Load each artefact affected by a current tag association write."""
    state = inspect(row)
    types = {row.artefact_type, *state.attrs.artefact_type.history.deleted}
    ids = {row.artefact_id, *state.attrs.artefact_id.history.deleted}
    for slug in types:
        model = TAGGED_MODELS.get(slug)
        if model is None:
            continue
        for artefact_id in ids - {None}:
            parent = session.get(model, artefact_id)
            if parent is not None and inspect(parent).persistent and parent not in session.deleted:
                yield parent


def _was_controlled(session, row) -> bool:
    """Include the persisted controlled kind before an attempted type change."""
    return (
        controlled(row)
        or isinstance(row, Document)
        and normalize_document_kind(_old_value(session, row, "doc_type")) in CONTROLLED_TYPES
    )


def _invalidate_review_write(session, row) -> None:
    """Return changed Review or Approval content to Draft within the current flush."""
    if not _was_controlled(session, row) or _approved(session, row):
        return
    slug, _ = artefact_identity(row)
    workflow = _workflow_for_write(session, row)
    if workflow is None:
        if str(_old_value(session, row, "status") or "").strip().lower() != "review":
            return
        workflow = ArtefactWorkflow(
            project_id=row.project_id,
            artefact_type=slug,
            artefact_id=row.id,
            revision_number=1,
            revision_creator_id=row.created_by_id,
            phase="Review",
            **{field: getattr(row, field, None) for field in SIGNOFF_FIELDS},
        )
        session.add(workflow)
    if workflow.phase not in {"Review", "Approval"}:
        return
    actor = audit_actor_var.get()
    _invalidate_cycle(session, row, workflow, actor[1] if actor else None)


def guard_workflow_writes(session) -> None:
    """Reject unpermitted controlled lifecycle writes and edits to approved archives/content."""
    permits = session.info.get("workflow_write_permits", {})
    review_changes = {}
    for row in tuple(session.dirty) + tuple(session.deleted):
        if isinstance(row, (ArtefactRevision, ArtefactRevisionFile)) and inspect(row).persistent:
            if row in session.deleted or session.is_modified(row, include_collections=False):
                raise HTTPException(
                    status_code=409,
                    detail="Approved revision content and file references are immutable.",
                )
        if isinstance(row, ArtefactWorkflow) and inspect(row).persistent:
            protected = {
                "phase",
                "revision_number",
                "revision_creator_id",
                "authorizing_change_id",
                "review_content_hash",
                "reviewed_by_id",
                "reviewed_at",
                "approved_by_id",
                "approved_at",
            }
            if any(
                inspect(row).attrs[field].history.has_changes() for field in protected
            ) and not permits.get((row.artefact_type, row.artefact_id)):
                raise HTTPException(
                    status_code=409,
                    detail="Workflow transitions require the authorized workflow operation.",
                )
        if (
            row in session.deleted
            or not inspect(row).persistent
            or not _was_controlled(session, row)
        ):
            continue
        state = inspect(row)
        changed = {
            attribute.key
            for attribute in state.mapper.column_attrs
            if state.attrs[attribute.key].history.has_changes()
        }
        authored = (_authored_fields(row) - IAM_FIELDS) | {
            "project_id",
            "id",
            "created_by_id",
            "status",
        }
        protected = authored | {"reviewed_by_id", "reviewed_at", "approved_by_id", "approved_at"}
        key = (artefact_identity(row)[0], row.id)
        if changed & (
            _authored_fields(row) | {"project_id", "id", "created_by_id"}
        ) and not permits.get(key):
            review_changes[key] = row
        if not changed & protected:
            continue
        approved = _approved(session, row)
        if approved and isinstance(row, ChangeRequest) and changed & authored:
            raise HTTPException(
                status_code=409, detail="Approved change requests cannot be edited."
            )
        if permits.get(key):
            continue
        if approved and changed & authored:
            raise HTTPException(
                status_code=409,
                detail="Approved content edits must use the authorized Save operation.",
            )
        if changed & {"status", "reviewed_by_id", "reviewed_at", "approved_by_id", "approved_at"}:
            raise HTTPException(
                status_code=409, detail="Use the document workflow for transitions and signoffs."
            )
    for child in tuple(session.new) + tuple(session.dirty) + tuple(session.deleted):
        if not isinstance(child, (DocumentSection, DocumentAttachment, TestSuiteItem, ArtefactTag)):
            continue
        if child in session.dirty and not session.is_modified(child, include_collections=False):
            continue
        parents = (
            _tag_parents(session, child)
            if isinstance(child, ArtefactTag)
            else _child_parents(session, child)
        )
        for parent in parents:
            key = (artefact_identity(parent)[0], parent.id)
            if (
                controlled(parent)
                and not isinstance(child, ArtefactTag)
                and _approved(session, parent)
                and not permits.get(key)
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Approved sections, files and suite membership must use an authorized Save operation.",
                )
            if not permits.get(key):
                review_changes[key] = parent
    for row in review_changes.values():
        _invalidate_review_write(session, row)
