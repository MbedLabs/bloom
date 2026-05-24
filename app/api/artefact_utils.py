"""Shared helpers for generic artefact detail endpoints."""

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import get_test_case_ids_verifying_requirements
from app.core.document_kinds import normalize_document_kind
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
from app.models.user import User
from app.schemas import (
    ArtefactActivityResponse,
    ArtefactRelatedResponse,
    RelatedDocumentSummary,
    RelatedProjectSummary,
    RelatedRequirementSummary,
    RelatedTestCaseSummary,
)

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


async def get_artefact_or_404(db: AsyncSession, artefact_type: str, artefact_id: int):
    model = ARTEFACT_MODELS.get(artefact_type)
    if not model:
        raise HTTPException(status_code=404, detail="Unsupported artefact type")

    artefact = (await db.execute(select(model).where(model.id == artefact_id))).scalar_one_or_none()
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
    db: AsyncSession, artefact_type: str, artefact_id: int
) -> ArtefactRelatedResponse:
    artefact = await get_artefact_or_404(db, artefact_type, artefact_id)
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
        requirements = (
            (
                await db.execute(
                    select(Requirement)
                    .where(Requirement.id.in_(requirement_ids))
                    .order_by(Requirement.req_id)
                )
            )
            .scalars()
            .all()
        )

    test_case_ids = await get_test_case_ids_verifying_requirements(requirement_ids, db)
    test_cases = []
    if test_case_ids:
        test_cases = (
            (
                await db.execute(
                    select(TestCase).where(TestCase.id.in_(test_case_ids)).order_by(TestCase.tc_id)
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
    for section in sections:
        if section.document_id not in documents_by_id:
            document = (
                await db.execute(select(Document).where(Document.id == section.document_id))
            ).scalar_one_or_none()
            if document:
                documents_by_id[section.document_id] = {
                    "document": document,
                    "matched_sections": [],
                }
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
