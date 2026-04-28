"""Read helpers for generic artefact links."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArtefactLink, Requirement, TestCase

VERIFY_LINK_ROLE = "verifies"
VERIFY_SOURCE_TYPE = "TC"
VERIFY_TARGET_TYPE = "REQ"


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
