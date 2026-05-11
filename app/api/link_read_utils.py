"""Read helpers for generic artefact links."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArtefactLink, Requirement, TestCase

VERIFY_LINK_ROLE = "verifies"
VERIFY_SOURCE_TYPE = "TC"
VERIFY_TARGET_TYPE = "REQ"

# Legacy requirement_links.link_type → artefact role (for ad-hoc SQL migration if needed).
LEGACY_REQ_LINK_TYPE_TO_ROLE = {
    "depends_on": "depends_on",
    "derived_from": "derives_from",
    "refines": "refines",
    "copies": "duplicates",
    "satisfies": "relates_to",
}


async def get_verifying_test_case_links_for_requirement(
    requirement_id: int, db: AsyncSession
) -> list[tuple[ArtefactLink, TestCase]]:
    result = await db.execute(
        select(ArtefactLink, TestCase)
        .join(TestCase, TestCase.id == ArtefactLink.source_id)
        .where(
            ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
            ArtefactLink.target_type == VERIFY_TARGET_TYPE,
            ArtefactLink.target_id == requirement_id,
            ArtefactLink.role == VERIFY_LINK_ROLE,
        )
        .order_by(ArtefactLink.created_at.desc(), TestCase.tc_id)
    )
    return list(result.all())


async def get_verified_requirement_links_for_test_case(
    test_case_id: int, db: AsyncSession
) -> list[tuple[ArtefactLink, Requirement]]:
    result = await db.execute(
        select(ArtefactLink, Requirement)
        .join(Requirement, Requirement.id == ArtefactLink.target_id)
        .where(
            ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
            ArtefactLink.target_type == VERIFY_TARGET_TYPE,
            ArtefactLink.source_id == test_case_id,
            ArtefactLink.role == VERIFY_LINK_ROLE,
        )
        .order_by(ArtefactLink.created_at.desc(), Requirement.req_id)
    )
    return list(result.all())


async def get_requirement_ids_verified_by_test_cases(
    test_case_ids: list[int], db: AsyncSession
) -> list[int]:
    if not test_case_ids:
        return []

    result = await db.execute(
        select(ArtefactLink.target_id)
        .where(
            ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
            ArtefactLink.target_type == VERIFY_TARGET_TYPE,
            ArtefactLink.source_id.in_(test_case_ids),
            ArtefactLink.role == VERIFY_LINK_ROLE,
        )
        .distinct()
    )
    return list(result.scalars().all())


async def get_test_case_ids_verifying_requirements(
    requirement_ids: list[int], db: AsyncSession
) -> list[int]:
    if not requirement_ids:
        return []

    result = await db.execute(
        select(ArtefactLink.source_id)
        .where(
            ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
            ArtefactLink.target_type == VERIFY_TARGET_TYPE,
            ArtefactLink.target_id.in_(requirement_ids),
            ArtefactLink.role == VERIFY_LINK_ROLE,
        )
        .distinct()
    )
    return list(result.scalars().all())


async def iter_req_req_incoming_neighbors(req_id: int, project_id: int, db: AsyncSession):
    """Edges (other_req_id -> req_id) with role (``artefact_links`` only)."""
    artefact_rows = await db.execute(
        select(ArtefactLink).where(
            ArtefactLink.project_id == project_id,
            ArtefactLink.source_type == "REQ",
            ArtefactLink.target_type == "REQ",
            ArtefactLink.target_id == req_id,
        )
    )
    for link in artefact_rows.scalars():
        yield link.source_id, link.role


async def iter_req_req_outgoing_neighbors(req_id: int, project_id: int, db: AsyncSession):
    """Edges (req_id -> other_req_id) with role (artefact_links only)."""
    artefact_rows = await db.execute(
        select(ArtefactLink).where(
            ArtefactLink.project_id == project_id,
            ArtefactLink.source_type == "REQ",
            ArtefactLink.target_type == "REQ",
            ArtefactLink.source_id == req_id,
        )
    )
    for link in artefact_rows.scalars():
        yield link.target_id, link.role


async def merged_linked_requirement_ids_for_test_concept(
    db: AsyncSession, concept_id: int, stored_ids: list | None
) -> list[int]:
    """REQ ids linked to a test concept via artefact_links (TCO->REQ) plus legacy JSON column."""
    from_links = (
        (
            await db.execute(
                select(ArtefactLink.target_id).where(
                    ArtefactLink.source_type == "TCO",
                    ArtefactLink.source_id == concept_id,
                    ArtefactLink.target_type == "REQ",
                )
            )
        )
        .scalars()
        .all()
    )
    legacy = list(stored_ids or [])
    merged = sorted({*from_links, *legacy})
    return merged
