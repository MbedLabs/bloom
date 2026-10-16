"""Read helpers for generic artefact links."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.link_rules import VERIFY_LINK_ROLE, VERIFY_SOURCE_TYPE, VERIFY_TARGET_TYPE
from app.core.security import apply_external_visibility_filter
from app.models import ArtefactLink, Requirement, TestCase
from app.models.user import User

# Legacy requirement_links.link_type → artefact role (for ad-hoc SQL migration if needed).
LEGACY_REQ_LINK_TYPE_TO_ROLE = {
    "depends_on": "depends_on",
    "derived_from": "derives_from",
    "refines": "refines",
    "copies": "duplicates",
    "satisfies": "relates_to",
}


async def _verify_link_rows(
    db: AsyncSession,
    anchor_column,
    anchor_id: int,
    other_model,
    other_column,
    other_order,
    current_user: User | None,
) -> list:
    """The verify links at one end of an anchor, each with the artefact at the other end."""
    query = (
        select(ArtefactLink, other_model)
        .join(other_model, other_model.id == other_column)
        .where(
            ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
            ArtefactLink.target_type == VERIFY_TARGET_TYPE,
            anchor_column == anchor_id,
            ArtefactLink.role == VERIFY_LINK_ROLE,
        )
        .order_by(ArtefactLink.created_at.desc(), other_order)
    )
    if current_user is not None:
        query = apply_external_visibility_filter(query, other_model, current_user)
    result = await db.execute(query)
    return list(result.all())


async def get_verifying_test_case_links_for_requirement(
    requirement_id: int,
    db: AsyncSession,
    current_user: User | None = None,
) -> list[tuple[ArtefactLink, TestCase]]:
    return await _verify_link_rows(
        db,
        ArtefactLink.target_id,
        requirement_id,
        TestCase,
        ArtefactLink.source_id,
        TestCase.tc_id,
        current_user,
    )


async def get_verified_requirement_links_for_test_case(
    test_case_id: int,
    db: AsyncSession,
    current_user: User | None = None,
) -> list[tuple[ArtefactLink, Requirement]]:
    return await _verify_link_rows(
        db,
        ArtefactLink.source_id,
        test_case_id,
        Requirement,
        ArtefactLink.target_id,
        Requirement.req_id,
        current_user,
    )


async def _verify_link_ends(db: AsyncSession, anchor_column, anchor_ids: list[int], other_column):
    """The distinct other ends of the verify links whose anchor end is one of the ids."""
    if not anchor_ids:
        return []

    result = await db.execute(
        select(other_column)
        .where(
            ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
            ArtefactLink.target_type == VERIFY_TARGET_TYPE,
            anchor_column.in_(anchor_ids),
            ArtefactLink.role == VERIFY_LINK_ROLE,
        )
        .distinct()
    )
    return list(result.scalars().all())


async def get_requirement_ids_verified_by_test_cases(
    test_case_ids: list[int], db: AsyncSession
) -> list[int]:
    return await _verify_link_ends(
        db, ArtefactLink.source_id, test_case_ids, ArtefactLink.target_id
    )


async def get_test_case_ids_verifying_requirements(
    requirement_ids: list[int], db: AsyncSession
) -> list[int]:
    return await _verify_link_ends(
        db, ArtefactLink.target_id, requirement_ids, ArtefactLink.source_id
    )


async def verify_link_counts(
    db: AsyncSession,
    anchor_column,
    anchor_ids: list[int],
    *,
    other_column=None,
    other_model=None,
    current_user=None,
) -> dict:
    """How many verify links each id has at the anchor end; an id without links counts 0.

    With ``other_column`` (the link column of the other end), ``other_model`` and
    ``current_user``, only links whose other end the user may see are counted."""
    counts = {anchor_id: 0 for anchor_id in anchor_ids}
    if anchor_ids:
        query = (
            select(anchor_column, func.count(ArtefactLink.id))
            .where(
                ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
                ArtefactLink.target_type == VERIFY_TARGET_TYPE,
                anchor_column.in_(anchor_ids),
                ArtefactLink.role == VERIFY_LINK_ROLE,
            )
            .group_by(anchor_column)
        )
        if other_model is not None:
            query = apply_external_visibility_filter(
                query.join(other_model, other_model.id == other_column), other_model, current_user
            )
        rows = (await db.execute(query)).all()
        counts.update({anchor_id: count for anchor_id, count in rows})
    return counts


async def _req_req_edges(req_id: int, project_id: int, db: AsyncSession, anchor: str, other: str):
    """Requirement-to-requirement links whose ``anchor`` end is the requirement."""
    artefact_rows = await db.execute(
        select(ArtefactLink).where(
            ArtefactLink.project_id == project_id,
            ArtefactLink.source_type == "REQ",
            ArtefactLink.target_type == "REQ",
            getattr(ArtefactLink, anchor) == req_id,
        )
    )
    for link in artefact_rows.scalars():
        yield getattr(link, other), link.role


async def iter_req_req_incoming_neighbors(req_id: int, project_id: int, db: AsyncSession):
    """Edges (other_req_id -> req_id) with role (``artefact_links`` only)."""
    async for edge in _req_req_edges(req_id, project_id, db, "target_id", "source_id"):
        yield edge


async def iter_req_req_outgoing_neighbors(req_id: int, project_id: int, db: AsyncSession):
    """Edges (req_id -> other_req_id) with role (artefact_links only)."""
    async for edge in _req_req_edges(req_id, project_id, db, "source_id", "target_id"):
        yield edge


async def merged_linked_requirement_ids_for_test_concept(
    db: AsyncSession, concept_id: int, stored_ids: list | None
) -> list[int]:
    """REQ ids linked to a test concept via artefact_links (CPT->REQ) plus legacy JSON column."""
    from_links = (
        (
            await db.execute(
                select(ArtefactLink.target_id).where(
                    ArtefactLink.source_type == "CPT",
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
