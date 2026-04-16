"""Shared helpers for generic artefact detail endpoints."""

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ArtefactActivity,
    ChangeRequest,
    DesignItem,
    Project,
    Requirement,
    RequirementTestCase,
    RiskItem,
    TestCase,
    TestConcept,
    Document,
    DocumentSection,
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


def build_activity_response(activity: ArtefactActivity) -> ArtefactActivityResponse:
    return ArtefactActivityResponse.model_validate(activity)


def get_allowed_transitions(artefact_type: str, current_status: str) -> list[str]:
    return WORKFLOW_TRANSITIONS.get(artefact_type, {}).get(current_status, [])


async def build_related_response(db: AsyncSession, artefact_type: str, artefact_id: int) -> ArtefactRelatedResponse:
    artefact = await get_artefact_or_404(db, artefact_type, artefact_id)
    project = (await db.execute(select(Project).where(Project.id == artefact.project_id))).scalar_one()

    requirement_ids: list[int] = []
    if artefact_type in {"design", "risk"}:
        linked_requirement_id = getattr(artefact, "linked_requirement_id", None)
        if linked_requirement_id:
            requirement_ids = [linked_requirement_id]
    elif artefact_type == "test-concept":
        requirement_ids = list(getattr(artefact, "linked_requirement_ids", []) or [])

    requirements = []
    if requirement_ids:
        requirements = (
            await db.execute(select(Requirement).where(Requirement.id.in_(requirement_ids)).order_by(Requirement.req_id))
        ).scalars().all()

    rtc_links = []
    if requirement_ids:
        rtc_links = (
            await db.execute(select(RequirementTestCase).where(RequirementTestCase.requirement_id.in_(requirement_ids)))
        ).scalars().all()

    test_case_ids = sorted({link.test_case_id for link in rtc_links})
    test_cases = []
    if test_case_ids:
        test_cases = (
            await db.execute(select(TestCase).where(TestCase.id.in_(test_case_ids)).order_by(TestCase.tc_id))
        ).scalars().all()

    sections = []
    if requirement_ids:
        sections = (
            await db.execute(select(DocumentSection).where(DocumentSection.linked_requirement_id.in_(requirement_ids)))
        ).scalars().all()

    documents_by_id: dict[int, dict[str, Any]] = {}
    for section in sections:
        if section.document_id not in documents_by_id:
            document = (await db.execute(select(Document).where(Document.id == section.document_id))).scalar_one_or_none()
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
            RelatedRequirementSummary(id=req.id, req_id=req.req_id, title=req.title, status=req.status)
            for req in requirements
        ],
        related_test_cases=[
            RelatedTestCaseSummary(id=tc.id, tc_id=tc.tc_id, title=tc.title, status=tc.status)
            for tc in test_cases
        ],
        related_documents=[
            RelatedDocumentSummary(
                id=item["document"].id,
                title=item["document"].title,
                doc_type=item["document"].doc_type,
                status=item["document"].status,
                matched_sections=item["matched_sections"],
            )
            for item in documents_by_id.values()
        ],
    )


def build_status_summary(user: User, current_status: str, next_status: str) -> str:
    return f"{user.full_name} changed status from {current_status} to {next_status}"
