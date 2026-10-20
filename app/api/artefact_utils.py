"""Shared helpers for generic artefact detail endpoints."""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import get_test_case_ids_verifying_requirements
from app.core.document_kinds import normalize_document_kind
from app.core.permissions import (
    DOC_TYPE_RESOURCES,
    VISIBILITIES,
    has_permission,
    transition_action,
)
from app.core.security import (
    access_terms,
    apply_external_visibility_filter,
    customer_only,
    doc_type_visible,
    effective_permissions,
    get_external_doc_types,
    holds_on_project,
    is_customer_only,
    require_project_access,
    row_allows,
    term_type_allows,
)
from app.models import (
    ArtefactActivity,
    ArtefactLink,
    ArtefactVisibility,
    ChangeRequest,
    Defect,
    DesignItem,
    Document,
    DocumentSection,
    Project,
    ReportRequest,
    Requirement,
    RiskItem,
    TestCampaign,
    TestCase,
    TestConcept,
    TestSuite,
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
from app.services.audit import audit_actor_var, record_audit_event

IN_PROGRESS = "In Progress"


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
    "test-suite": TestSuite,
    "campaign": TestCampaign,
}

ARTEFACT_LINK_TYPES = {
    "design": "DES",
    "risk": "RSK",
    "change": "CHG",
    "test-concept": "CPT",
    "defect": "DEF",
    "requirement": "REQ",
    "test-case": "TC",
    "test-suite": "TS",
    "campaign": "CMP",
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
        "Triaged": [IN_PROGRESS, "Rejected", "Duplicate"],
        IN_PROGRESS: ["Resolved", "Triaged"],
        "Resolved": ["Verified", IN_PROGRESS],
        "Verified": ["Closed", IN_PROGRESS],
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
    context_actor = audit_actor_var.get()
    actor_id = context_actor[1] if context_actor and context_actor[0] == "user" else None
    db.add(
        ArtefactActivity(
            artefact_type=artefact_type,
            artefact_id=artefact_id,
            event_type=event_type,
            summary=summary,
            actor_user_id=actor_id,
        )
    )
    await db.flush()


WORKFLOW_ACTIVITY_FIELDS = frozenset({"status"})

ARTEFACT_PUBLIC_ID_ATTRS = {
    "requirement": "req_id",
    "test-case": "tc_id",
    "document": "doc_id",
    "design": "design_id",
    "risk": "risk_id",
    "change": "change_id",
    "test-concept": "concept_id",
    "defect": "defect_id",
    "test-suite": "suite_id",
    "campaign": "campaign_id",
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
) -> None:
    if previous_status == next_status:
        return

    event = _workflow_status_event_for_target(next_status)
    if event == "reviewed":
        await log_artefact_activity(
            db,
            artefact_type,
            artefact_id,
            "reviewed",
            f"{actor.full_name} marked {public_id} reviewed",
        )
        return
    if event == "approved":
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


def build_activity_response(
    activity: ArtefactActivity, actor: Optional[User] = None
) -> ArtefactActivityResponse:
    result = ArtefactActivityResponse.model_validate(activity)
    result.actor_name = actor.full_name if actor else None
    result.actor_profile_picture_url = actor.profile_picture_url if actor else None
    return result


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
    types = await visible_types(db, current_user, artefact.project_id)

    requirement_ids: list[int] = []
    requirement_ids.extend(
        await _get_related_requirement_ids_from_links(db, artefact_type, artefact_id)
    )
    requirement_ids = sorted(set(requirement_ids))

    requirements = []
    if requirement_ids:
        requirements_query = (
            select(Requirement)
            .where(Requirement.id.in_(requirement_ids), type_visible(types, "REQ"))
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
            select(TestCase)
            .where(TestCase.id.in_(test_case_ids), type_visible(types, "TC"))
            .order_by(TestCase.tc_id)
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

    documents_by_id: dict[int, dict[str, Any]] = {}
    section_document_ids = {section.document_id for section in sections}
    if section_document_ids:
        visible_documents = (
            (
                await db.execute(
                    apply_external_visibility_filter(
                        select(Document).where(
                            Document.id.in_(section_document_ids),
                            Document.doc_type.in_(types) if types is not None else True,
                        ),
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
    if model is Document:
        await db.execute(
            update(ReportRequest)
            .where(ReportRequest.document_id == row.id)
            .values(document_id=None)
        )
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

    A row the user may not see, one in a project the user is not in, one whose document
    type is outside an external user's allowlist and, with any action, one whose document
    type the user holds no view on are a 404, checked before any 403. With ``permission=(action, resource)`` the action is checked on the resource, the
    row's own document type when the resource is None, and a missing permission is a 403;
    an external user's changing action on a row they did not create is a 403.
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
    await require_project_access(db, current_user, row.project_id, outsider=hidden)
    if resource in DOC_TYPE_RESOURCES and not await doc_type_visible(
        db, current_user, row.project_id, resource
    ):
        raise hidden
    if (
        action
        and resource in DOC_TYPE_RESOURCES
        and not await holds(db, current_user, row.project_id, "view", resource)
    ):
        raise hidden
    if action and action != "view":
        if not await row_allows(db, current_user, row, action, resource):
            raise HTTPException(
                status_code=403, detail=f"Missing permission: {action} on {resource}."
            )
        if action in OWN_ONLY_ACTIONS and not changes_allowed(current_user, row):
            raise HTTPException(status_code=403, detail=CHANGES_OWN_ONLY)
    return row


OWN_ONLY_ACTIONS = ("edit", "delete", "plan", "review", "approve")

FIRST_STATUS = {
    "REQ": "Draft",
    "TC": "Draft",
    "SPEC": "Draft",
    "PRT": "Draft",
    "RPT": "Draft",
    "STD": "Draft",
    "TS": "Draft",
    "DES": "Draft",
    "CPT": "Draft",
    "RSK": "Open",
    "DEF": "Open",
    "CHG": "Draft",
    "CMP": "Planned",
}

FIXED_STATUS_KINDS = frozenset({"DEF", "RSK", "CHG", "CMP"})


CHANGES_OWN_ONLY = "External users change only what they created."


def changes_allowed(user: User, row) -> bool:
    """False when the user's access on the row's project is customer-only and they did not
    create the row; a row with no recorded creator is another's."""
    if not hasattr(row, "created_by_id") or not customer_only(user):
        return True
    return row.created_by_id == user.id


def requirement_origin_visibility(req_origin: str | None) -> str:
    """The visibility a requirement origin gives: customer for Customer, else internal."""
    customer = (req_origin or "").strip().lower() == ArtefactVisibility.customer.value
    return ArtefactVisibility.customer.value if customer else ArtefactVisibility.internal.value


def external_create_values(user: User, type_code: str, named: dict) -> dict:
    """Apply an external account's customer visibility and initial workflow values."""
    if user.role != UserRole.external:
        return {}
    customer = ArtefactVisibility.customer.value
    if named.get("visibility", customer) != customer or (
        type_code == "REQ"
        and requirement_origin_visibility(named.get("req_origin", customer)) != customer
    ):
        raise HTTPException(
            status_code=403, detail="External users create customer artefacts only."
        )
    first = FIRST_STATUS[type_code]
    if named.get("status", first) != first:
        raise HTTPException(status_code=403, detail=f"External users create in status {first}.")
    values = {"visibility": customer, "status": first}
    if type_code == "REQ":
        values["req_origin"] = "Customer"
    return values


def check_external_change(user: User, type_code: str, row, changes: dict) -> None:
    """Refuse with 403 an external user's change of the row's visibility (for a
    requirement, of an origin giving another visibility) and of its status other than to
    Draft, or of any status on defects, risks, changes and campaigns. ``changes`` holds the
    fields the request sets; a value equal to the stored one is no change."""
    if not customer_only(user):
        return
    visibility = changes.get("visibility")
    if type_code == "REQ" and changes.get("req_origin") is not None:
        visibility = requirement_origin_visibility(changes["req_origin"])
    if visibility is not None and visibility != row.visibility:
        raise HTTPException(status_code=403, detail="External users cannot change visibility.")
    status = changes.get("status")
    if status is None or status == row.status:
        return
    if type_code in FIXED_STATUS_KINDS:
        raise HTTPException(
            status_code=403,
            detail="External users do not change the status of defects, risks, changes or campaigns.",
        )
    if status != "Draft":
        raise HTTPException(status_code=403, detail="External users set the status only to Draft.")


async def holds(
    db: AsyncSession, user: User, project_id: int, action: str, resource: str | None
) -> bool:
    """Whether one term of the user on the project grants the action on the resource;
    an administrator holds every action."""
    return await holds_on_project(db, user, project_id, action, resource)


async def fully_visible_types(
    db: AsyncSession, user: User, project_id: int
) -> frozenset[str] | None:
    """The document types of which the user sees every row in the project: types their
    view terms there cover at every visibility together; None for an administrator."""
    if user.role == UserRole.admin:
        return None
    terms = await access_terms(db, user, project_id)
    visible = set()
    for code in DOC_TYPE_RESOURCES:
        covered: set = set()
        for term in terms:
            if term.customer_only or not term_type_allows(term, "view", code):
                continue
            covered |= set(VISIBILITIES) if term.visibilities is None else term.visibilities
        if set(VISIBILITIES) <= covered:
            visible.add(code)
    return frozenset(visible)


async def visible_types(db: AsyncSession, user: User, project_id: int) -> frozenset[str] | None:
    """The document types the user sees in the project: those one of their terms there
    grants view on and covers; None for an administrator, who sees every type."""
    if user.role == UserRole.admin:
        return None
    terms = await access_terms(db, user, project_id)
    return frozenset(
        code
        for code in DOC_TYPE_RESOURCES
        if any(term_type_allows(term, "view", code) for term in terms)
    )


def type_visible(types: frozenset[str] | None, type_code: str | None) -> bool:
    """Whether a type is in a set from `visible_types`; None means every type."""
    return types is None or type_code in types


async def row_visible_to(db: AsyncSession, user: User, row, resource: str | None) -> bool:
    """Whether one term of the user on the row's project grants view on its type and
    covers the row (R-u)."""
    return await row_allows(db, user, row, "view", resource)


async def may_sign_as(
    db: AsyncSession,
    user: User | None,
    project_id: int,
    type_code: str,
    step: str,
    row=None,
    visibility: str | None = None,
) -> bool:
    """Check active project authority and visible scope for review or internal approval."""
    if user is None or not user.is_active or (step == "approve" and is_customer_only(user)):
        return False
    if row is not None:
        return await row_allows(
            db, user, row, "view", type_code, visibility=visibility
        ) and await row_allows(db, user, row, step, type_code, visibility=visibility)
    return await holds(db, user, project_id, "view", type_code) and await holds(
        db, user, project_id, step, type_code
    )


async def assignee_can_sign(
    db: AsyncSession, user_id: int | None, project_id: int, type_code: str, step: str, row=None
) -> bool | None:
    """Whether the stored assignee could sign the step; None without an assignee."""
    if not user_id:
        return None
    return await may_sign_as(db, await db.get(User, user_id), project_id, type_code, step, row)


async def check_assignee(
    db: AsyncSession,
    project_id: int,
    type_code: str,
    public_id: str,
    step: str,
    user_id: int | None,
    row=None,
    visibility: str | None = None,
) -> None:
    """Refuse with 422 a new reviewer (step review) or approver (step approve) who could not
    sign: an external user, or one without view and the step on the type in the project. An
    id with no user is left to the route."""
    assignee = await db.get(User, user_id) if user_id is not None else None
    if assignee is None:
        return
    if not await may_sign_as(db, assignee, project_id, type_code, step, row, visibility):
        role = "reviewer" if step == "review" else "approver"
        raise HTTPException(
            status_code=422,
            detail=f"The {role} cannot see {public_id} or does not hold {step} on {type_code}.",
        )


async def check_assignees_keep_sight(
    db: AsyncSession, row, public_id: str, visibility: str | None
) -> None:
    """Refuse with 409 a change to the visibility that would hide the row from its stored
    reviewer or approver: one who sees the row now and would not with the new visibility."""
    if visibility is None or visibility == row.visibility:
        return
    for attr, role in (("reviewer_id", "reviewer"), ("approver_id", "approver")):
        user_id = getattr(row, attr, None)
        assignee = await db.get(User, user_id) if user_id else None
        if (
            assignee is not None
            and await row_allows(db, assignee, row, "view")
            and not await row_allows(db, assignee, row, "view", visibility=visibility)
        ):
            raise HTTPException(
                status_code=409, detail=f"The {role} could no longer see {public_id}."
            )


async def check_visibility_right(
    db: AsyncSession, user: User, type_code: str, row, changes: dict
) -> None:
    """Refuse with 403 an update that changes the row's visibility (for a requirement, its
    origin to one giving another visibility) unless one edit term of the user on the type
    ticks the new visibility."""
    if type_code == "REQ":
        origin = changes.get("req_origin")
        visibility = requirement_origin_visibility(origin) if origin is not None else None
    else:
        visibility = changes.get("visibility")
    if visibility is None or visibility == getattr(row, "visibility", None):
        return
    if user.role == UserRole.admin:
        return
    if not any(
        term_type_allows(term, "edit", type_code)
        and (term.visibilities is None or visibility in term.visibilities)
        for term in await access_terms(db, user, row.project_id)
    ):
        raise HTTPException(status_code=403, detail="No edit policy covers this visibility.")


async def check_status_right(
    db: AsyncSession, user: User, type_code: str, row, changes: dict
) -> None:
    """Refuse with 403 an update whose change of the stored status needs a right the user
    lacks on the type: approve for Approved and Rejected, review when leaving Review or
    Analysis. ``changes`` holds the fields the request sets; edit is the route's own check."""
    status = changes.get("status")
    if status is None or status == row.status:
        return
    from app.services.document_workflow import controlled

    if controlled(row):
        raise HTTPException(status_code=409, detail="Use the document workflow for status changes.")
    action = transition_action(row.status, status)
    if action != "edit" and not await row_allows(db, user, row, action, type_code):
        raise HTTPException(status_code=403, detail=f"Missing permission: {action} on {type_code}.")


async def check_create_status_right(
    db: AsyncSession, user: User, project_id: int, type_code: str, named: dict
) -> None:
    """Refuse with 403 a create naming Approved or Rejected when the user lacks approve on the
    type. ``named`` holds the fields the request names."""
    from app.services.document_workflow import CONTROLLED_TYPES

    status = named.get("status")
    if type_code in CONTROLLED_TYPES and status not in (None, "Draft"):
        raise HTTPException(status_code=422, detail="New controlled documents start in Draft.")
    if status is not None and transition_action(FIRST_STATUS[type_code], status) == "approve":
        await require_project_access(db, user, project_id, permission=("approve", type_code))


async def allowed_actions(db: AsyncSession, user: User, row, resource: str) -> list[str]:
    """The changing actions the user may take on a row they can see: every one for an
    administrator; for others those one of their terms grants on the row and covers it
    (R-u), and none on a row they did not create when their access is customer-only."""
    from app.api.workflow import can_comment

    actions = []
    if changes_allowed(user, row):
        actions = [
            action
            for action in OWN_ONLY_ACTIONS
            if await row_allows(db, user, row, action, resource)
        ]
    if await can_comment(db, user, row):
        actions.append("comment")
    return actions


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


async def prepare_workflow_update(db, row, data, actor) -> None:
    """Validate authored writes and keep an invalidated review in Draft."""
    from app.services.document_workflow import prepare_content_write

    prior_status = row.status
    prior_version = getattr(row, "version", None)
    changes = data.model_dump(exclude_unset=True)
    await prepare_content_write(db, row, actor, changes)
    if "status" in changes and changes["status"] == prior_status and row.status != prior_status:
        data.status = row.status
    if "version" in changes and changes["version"] == prior_version:
        data.version = row.version
