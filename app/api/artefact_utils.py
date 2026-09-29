"""Shared helpers for generic artefact detail endpoints."""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import get_test_case_ids_verifying_requirements
from app.core.document_kinds import normalize_document_kind
from app.core.permissions import DOC_TYPE_RESOURCES
from app.core.security import (
    apply_external_visibility_filter,
    external_doc_type_allowed,
    get_external_doc_types,
    require_project_access,
)
from app.models import (
    ArtefactActivity,
    ArtefactLink,
    ChangeRequest,
    Defect,
    DesignItem,
    Document,
    DocumentSection,
    Project,
    Requirement,
    RiskItem,
    TestCase,
    TestConcept,
)
from app.models.user import User, UserRole
from app.schemas import (
    ArtefactActivityResponse,
    ArtefactRelatedResponse,
    RelatedDocumentSummary,
    RelatedProjectSummary,
    RelatedRequirementSummary,
    RelatedTestCaseSummary,
    RequirementSummary,
    TestCaseSummary,
)
from app.services.audit import record_audit_event


def naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    """The value as a naive UTC datetime; a naive value is returned unchanged."""
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def minute_utc(value: Optional[datetime]) -> str:
    """The time as ``YYYY-MM-DD HH:MM UTC``, Bloom's precision for people; empty when None."""
    stamp = naive_utc(value)
    return stamp.strftime("%Y-%m-%d %H:%M UTC") if stamp else ""


def requirement_summary(req: Requirement) -> RequirementSummary:
    """The id, public id, title and status of a requirement."""
    return RequirementSummary(id=req.id, req_id=req.req_id, title=req.title, status=req.status)


def test_case_summary(tc: TestCase) -> TestCaseSummary:
    """The id, public id, title and status of a test case."""
    return TestCaseSummary(id=tc.id, tc_id=tc.tc_id, title=tc.title, status=tc.status)


ARTEFACT_MODELS = {
    "design": DesignItem,
    "risk": RiskItem,
    "change": ChangeRequest,
    "test-concept": TestConcept,
    "defect": Defect,
    "requirement": Requirement,
    "test-case": TestCase,
    "document": Document,
}

ARTEFACT_LINK_TYPES = {
    "design": "DES",
    "risk": "RSK",
    "change": "CHG",
    "test-concept": "CPT",
    "defect": "DEF",
}

WORKFLOW_TRANSITIONS = {
    "design": {
        "Draft": ["Review"],
        "Review": ["Approved", "Draft"],
        "Approved": ["Review"],
    },
    "risk": {
        "Open": ["Monitoring", "Mitigated", "Closed"],
        "Monitoring": ["Mitigated", "Closed"],
        "Mitigated": ["Closed", "Monitoring"],
        "Closed": ["Open"],
    },
    "change": {
        "Submitted": ["Analysis", "Rejected"],
        "Analysis": ["Approved", "Rejected"],
        "Approved": ["Implemented", "Rejected"],
        "Implemented": ["Approved"],
        "Rejected": ["Submitted"],
    },
    "test-concept": {
        "Draft": ["Review"],
        "Review": ["Approved", "Draft"],
        "Approved": ["Review"],
    },
    "defect": {
        "Open": ["Triaged", "Rejected", "Duplicate"],
        "Triaged": ["In Progress", "Rejected", "Duplicate"],
        "In Progress": ["Resolved", "Triaged"],
        "Resolved": ["Verified", "In Progress"],
        "Verified": ["Closed", "In Progress"],
        "Closed": ["Open"],
        "Rejected": ["Open"],
        "Duplicate": ["Open"],
    },
}


async def get_artefact_or_404(
    db: AsyncSession,
    artefact_type: str,
    artefact_id: int | str,
    current_user: User | None = None,
):
    model = ARTEFACT_MODELS.get(artefact_type)
    if not model:
        raise HTTPException(status_code=404, detail="Unsupported artefact type")

    id_text = str(artefact_id)
    public_attr = ARTEFACT_PUBLIC_ID_ATTRS.get(artefact_type)
    if id_text.isdigit():
        query = select(model).where(model.id == int(id_text))
    elif public_attr and hasattr(model, public_attr):
        query = select(model).where(getattr(model, public_attr) == id_text)
    else:
        raise HTTPException(status_code=404, detail="Artefact not found")
    if current_user is not None and hasattr(model, "visibility"):
        query = apply_external_visibility_filter(query, model, current_user)

    artefact = (await db.execute(query)).scalar_one_or_none()
    if not artefact:
        raise HTTPException(status_code=404, detail="Artefact not found")
    return artefact


async def log_artefact_activity(
    db: AsyncSession,
    artefact_type: str,
    artefact_id: int,
    event_type: str,
    summary: str,
):
    db.add(
        ArtefactActivity(
            artefact_type=artefact_type,
            artefact_id=artefact_id,
            event_type=event_type,
            summary=summary,
        )
    )
    await db.flush()


WORKFLOW_ACTIVITY_FIELDS = frozenset(
    {
        "reviewed_by_id",
        "reviewed_at",
        "approved_by_id",
        "approved_at",
        "status",
    }
)

ARTEFACT_PUBLIC_ID_ATTRS = {
    "requirement": "req_id",
    "test-case": "tc_id",
    "document": "doc_id",
    "design": "design_id",
    "risk": "risk_id",
    "change": "change_id",
    "test-concept": "concept_id",
    "defect": "defect_id",
}


def artefact_public_id(artefact_type: str, artefact: Any) -> str:
    attr = ARTEFACT_PUBLIC_ID_ATTRS.get(artefact_type, "id")
    value = getattr(artefact, attr, None)
    return str(value if value is not None else artefact.id)


def _workflow_status_event_for_target(next_status: str) -> str | None:
    normalized = next_status.strip().lower()
    if normalized == "review":
        return "reviewed"
    if normalized == "approved":
        return "approved"
    return None


async def log_workflow_status_transition(
    db: AsyncSession,
    *,
    artefact_type: str,
    artefact_id: int,
    public_id: str,
    actor: User,
    previous_status: str,
    next_status: str,
    skip_reviewed: bool = False,
    skip_approved: bool = False,
) -> None:
    if previous_status == next_status:
        return

    event = _workflow_status_event_for_target(next_status)
    if event == "reviewed" and not skip_reviewed:
        await log_artefact_activity(
            db,
            artefact_type,
            artefact_id,
            "reviewed",
            f"{actor.full_name} marked {public_id} reviewed",
        )
        return
    if event == "approved" and not skip_approved:
        await log_artefact_activity(
            db,
            artefact_type,
            artefact_id,
            "approved",
            f"{actor.full_name} marked {public_id} approved",
        )
        return

    await log_artefact_activity(
        db,
        artefact_type,
        artefact_id,
        "status_changed",
        build_status_summary(actor, previous_status, next_status),
    )


async def log_document_workflow_activity_from_patch(
    db: AsyncSession,
    *,
    artefact_type: str,
    artefact_id: int,
    public_id: str,
    actor: User,
    fields_set: set[str],
    previous_status: str | None = None,
    next_status: str | None = None,
) -> None:
    if fields_set.intersection({"reviewed_by_id", "reviewed_at"}):
        await log_artefact_activity(
            db,
            artefact_type,
            artefact_id,
            "reviewed",
            f"{actor.full_name} marked {public_id} reviewed",
        )
    if fields_set.intersection({"approved_by_id", "approved_at"}):
        await log_artefact_activity(
            db,
            artefact_type,
            artefact_id,
            "approved",
            f"{actor.full_name} marked {public_id} approved",
        )
    if (
        "status" in fields_set
        and previous_status is not None
        and next_status is not None
        and previous_status != next_status
    ):
        await log_workflow_status_transition(
            db,
            artefact_type=artefact_type,
            artefact_id=artefact_id,
            public_id=public_id,
            actor=actor,
            previous_status=previous_status,
            next_status=next_status,
            skip_reviewed=bool(fields_set.intersection({"reviewed_by_id", "reviewed_at"})),
            skip_approved=bool(fields_set.intersection({"approved_by_id", "approved_at"})),
        )


def should_log_generic_document_update(fields_set: set[str]) -> bool:
    return not fields_set.issubset(WORKFLOW_ACTIVITY_FIELDS)


FIELD_LABELS: dict[str, str] = {
    "title": "title",
    "description": "description",
    "content_json": "content",
    "content_html": "content",
    "priority": "priority",
    "severity": "severity",
    "req_type": "type",
    "req_origin": "origin",
    "design_type": "design type",
    "category": "category",
    "change_type": "change type",
    "probability": "probability",
    "coverage": "coverage",
    "resolution_summary": "resolution",
    "reviewed_by_id": "reviewer",
    "approved_by_id": "approver",
}


def updated_summary(
    actor_full_name: str, artefact_label: str, public_id: str, fields_set: set[str]
) -> str:
    """Build activity summary with field names: "User changed title, status on REQ-001"."""
    changed = sorted(
        FIELD_LABELS.get(f, f) for f in fields_set if f not in WORKFLOW_ACTIVITY_FIELDS
    )
    if not changed:
        return f"{actor_full_name} updated {artefact_label} {public_id}"
    field_list = ", ".join(changed)
    return f"{actor_full_name} changed {field_list} on {artefact_label} {public_id}"


def build_activity_response(activity: ArtefactActivity) -> ArtefactActivityResponse:
    return ArtefactActivityResponse.model_validate(activity)


def get_allowed_transitions(artefact_type: str, current_status: str) -> list[str]:
    return WORKFLOW_TRANSITIONS.get(artefact_type, {}).get(current_status, [])


async def _get_related_requirement_ids_from_links(
    db: AsyncSession, artefact_type: str, artefact_id: int
) -> list[int]:
    artefact_link_type = ARTEFACT_LINK_TYPES.get(artefact_type)
    if not artefact_link_type:
        return []

    outgoing_rows = (
        (
            await db.execute(
                select(ArtefactLink.target_id).where(
                    ArtefactLink.source_type == artefact_link_type,
                    ArtefactLink.source_id == artefact_id,
                    ArtefactLink.target_type == "REQ",
                )
            )
        )
        .scalars()
        .all()
    )
    incoming_rows = (
        (
            await db.execute(
                select(ArtefactLink.source_id).where(
                    ArtefactLink.target_type == artefact_link_type,
                    ArtefactLink.target_id == artefact_id,
                    ArtefactLink.source_type == "REQ",
                )
            )
        )
        .scalars()
        .all()
    )
    return sorted({*outgoing_rows, *incoming_rows})


async def build_related_response(
    db: AsyncSession, artefact_type: str, artefact_id: int | str, current_user: User
) -> ArtefactRelatedResponse:
    artefact = await get_artefact_or_404(db, artefact_type, artefact_id, current_user)
    artefact_id = artefact.id
    project = (
        await db.execute(select(Project).where(Project.id == artefact.project_id))
    ).scalar_one()

    requirement_ids: list[int] = []
    requirement_ids.extend(
        await _get_related_requirement_ids_from_links(db, artefact_type, artefact_id)
    )
    requirement_ids = sorted(set(requirement_ids))

    requirements = []
    if requirement_ids:
        requirements_query = (
            select(Requirement)
            .where(Requirement.id.in_(requirement_ids))
            .order_by(Requirement.req_id)
        )
        requirements = (
            (
                await db.execute(
                    apply_external_visibility_filter(requirements_query, Requirement, current_user)
                )
            )
            .scalars()
            .all()
        )
        requirement_ids = [req.id for req in requirements]

    test_case_ids = await get_test_case_ids_verifying_requirements(requirement_ids, db)
    test_cases = []
    if test_case_ids:
        test_case_query = (
            select(TestCase).where(TestCase.id.in_(test_case_ids)).order_by(TestCase.tc_id)
        )
        test_cases = (
            (
                await db.execute(
                    apply_external_visibility_filter(test_case_query, TestCase, current_user)
                )
            )
            .scalars()
            .all()
        )

    sections = []
    if requirement_ids:
        sections = (
            (
                await db.execute(
                    select(DocumentSection).where(
                        DocumentSection.linked_requirement_id.in_(requirement_ids)
                    )
                )
            )
            .scalars()
            .all()
        )

    # Fetch every parent document at once.
    documents_by_id: dict[int, dict[str, Any]] = {}
    section_document_ids = {section.document_id for section in sections}
    if section_document_ids:
        visible_documents = (
            (
                await db.execute(
                    apply_external_visibility_filter(
                        select(Document).where(Document.id.in_(section_document_ids)),
                        Document,
                        current_user,
                    )
                )
            )
            .scalars()
            .all()
        )
        documents_by_id = {
            document.id: {"document": document, "matched_sections": []}
            for document in visible_documents
        }

    for section in sections:
        if section.document_id in documents_by_id:
            documents_by_id[section.document_id]["matched_sections"].append(section.title)

    return ArtefactRelatedResponse(
        project=RelatedProjectSummary(
            id=project.id,
            name=project.name,
            prefix=project.prefix,
            status=project.status,
        ),
        linked_requirements=[
            RelatedRequirementSummary(
                id=req.id, req_id=req.req_id, title=req.title, status=req.status
            )
            for req in requirements
        ],
        related_test_cases=[
            RelatedTestCaseSummary(id=tc.id, tc_id=tc.tc_id, title=tc.title, status=tc.status)
            for tc in test_cases
        ],
        related_documents=[
            RelatedDocumentSummary(
                id=item["document"].id,
                doc_id=item["document"].doc_id,
                title=item["document"].title,
                doc_type=normalize_document_kind(item["document"].doc_type),
                status=item["document"].status,
                matched_sections=item["matched_sections"],
            )
            for item in documents_by_id.values()
        ],
    )


def build_status_summary(user: User, current_status: str, next_status: str) -> str:
    return f"{user.full_name} changed status from {current_status} to {next_status}"


AUDIT_PUBLIC_ID_ATTRS = {
    **ARTEFACT_PUBLIC_ID_ATTRS,
    "test-suite": "suite_id",
    "campaign": "campaign_id",
    "baseline": "baseline_id",
}


def _audit_public_id(artefact_type: str, artefact: Any) -> str:
    """The public id of an artefact, or its database id when it has none."""
    value = getattr(artefact, AUDIT_PUBLIC_ID_ATTRS.get(artefact_type, "id"), None)
    return str(value if value is not None else artefact.id)


async def audit_artefact_deleted(db: AsyncSession, artefact_type: str, artefact: Any) -> None:
    """Record the deletion of an artefact in the audit log."""
    await record_audit_event(
        db,
        "artefact.deleted",
        target_type=artefact_type,
        target_id=_audit_public_id(artefact_type, artefact),
        project_id=getattr(artefact, "project_id", None),
    )


async def audit_visibility_change(
    db: AsyncSession, artefact_type: str, artefact: Any, previous: Any
) -> None:
    """Record a change of an artefact's visibility in the audit log, if it changed."""
    current = getattr(artefact, "visibility", None)
    previous_value = getattr(previous, "value", previous)
    current_value = getattr(current, "value", current)
    if previous_value == current_value:
        return
    await record_audit_event(
        db,
        "artefact.visibility_changed",
        target_type=artefact_type,
        target_id=_audit_public_id(artefact_type, artefact),
        project_id=getattr(artefact, "project_id", None),
        details={"from": previous_value, "to": current_value},
    )


async def get_row_or_404(db: AsyncSession, model, item_id: int, detail: str, *conditions):
    """The row of the model with the id that meets the conditions, or a 404 with the detail."""
    row = (
        await db.execute(select(model).where(model.id == item_id, *conditions))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail=detail)
    return row


async def delete_project_row(
    db: AsyncSession,
    current_user: User,
    model,
    item_id: int,
    not_found: str,
    *,
    resource: str | None = None,
    audit_type: str | None = None,
    activity: tuple[str, str] | None = None,
) -> None:
    """Delete a project row after the delete permission check on the resource.

    Without a resource the row's own document type is checked. ``activity`` is the
    label and public id attribute of an activity entry under ``audit_type``; with an
    ``audit_type`` the deletion is audited.
    """
    row = await get_visible_row(
        db, model, item_id, not_found, current_user, permission=("delete", resource)
    )
    if activity:
        label, id_attr = activity
        await log_artefact_activity(
            db,
            audit_type,
            row.id,
            "deleted",
            f"{current_user.full_name} deleted {label} {getattr(row, id_attr)}",
        )
    if audit_type:
        await audit_artefact_deleted(db, audit_type, row)
    await db.delete(row)


async def get_visible_row(
    db: AsyncSession,
    model,
    item_id: int,
    not_found: str,
    current_user: User,
    *,
    permission: tuple[str, str | None] | None = None,
):
    """The row with the id when the user may see it and act on it, else 404 or 403.

    A row the user may not see, or one in a project the user is not in, is a 404. With
    ``permission=(action, resource)`` the action is checked on the resource, the row's
    own document type when the resource is None, and a document type outside an
    external user's allowlist is a 404; a missing permission is a 403.
    """
    query = select(model).where(model.id == item_id)
    if hasattr(model, "visibility"):
        query = apply_external_visibility_filter(query, model, current_user)
    row = (await db.execute(query)).scalar_one_or_none()
    hidden = HTTPException(status_code=404, detail=not_found)
    if not row:
        raise hidden
    action, resource = permission or (None, None)
    resource = resource or getattr(row, "doc_type", None)
    await require_project_access(
        db,
        current_user,
        row.project_id,
        permission=(action, resource) if action else None,
        outsider=hidden,
    )
    if (
        current_user.role == UserRole.external
        and resource in DOC_TYPE_RESOURCES
        and not external_doc_type_allowed(
            current_user, await get_external_doc_types(db, current_user, row.project_id), resource
        )
    ):
        raise hidden
    return row


async def apply_update(db: AsyncSession, row, data, audit_type: str) -> None:
    """Set the update's fields on the row, audit a visibility change and reload the row."""
    previous_visibility = getattr(row, "visibility", None)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await audit_visibility_change(db, audit_type, row, previous_visibility)
    await db.flush()
    await db.refresh(row)


async def page_of(db: AsyncSession, base, model, skip: int, limit: int) -> tuple[list, int]:
    """One page of the query's rows, newest first, and the total number of rows."""
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (
        (await db.execute(base.order_by(model.created_at.desc()).offset(skip).limit(limit)))
        .scalars()
        .all()
    )
    return list(rows), total
