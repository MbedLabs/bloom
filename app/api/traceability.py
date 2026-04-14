"""
Traceability matrix API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Requirement, RequirementTestCase, TestCase, TestRunLink
from app.schemas import (
    TraceabilityItem,
    RequirementResponse,
    TestCaseResponse,
    TestRunLinkResponse,
)

router = APIRouter()


@router.get("", response_model=list[TraceabilityItem])
async def get_traceability_matrix(
    project_id: int = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a traceability matrix for a project.

    Returns each requirement with its linked test cases, test runs,
    and coverage status (Covered / Partial / Uncovered).
    """
    result = await db.execute(
        select(Requirement).where(Requirement.project_id == project_id)
    )
    requirements = result.scalars().all()

    items = []
    for req in requirements:
        tc_links_result = await db.execute(
            select(RequirementTestCase).where(
                RequirementTestCase.requirement_id == req.id
            )
        )
        tc_links = tc_links_result.scalars().all()

        linked_test_cases = []
        for link in tc_links:
            tc_result = await db.execute(
                select(TestCase).where(TestCase.id == link.test_case_id)
            )
            tc = tc_result.scalar_one_or_none()
            if tc:
                linked_test_cases.append(TestCaseResponse(
                    id=tc.id,
                    project_id=tc.project_id,
                    tc_id=tc.tc_id,
                    title=tc.title,
                    description=tc.description,
                    preconditions=tc.preconditions,
                    steps=tc.steps,
                    status=tc.status,
                    created_at=tc.created_at,
                    updated_at=tc.updated_at,
                    requirement_count=0,
                ))

        tr_links_result = await db.execute(
            select(TestRunLink).where(TestRunLink.requirement_id == req.id)
        )
        tr_links = tr_links_result.scalars().all()

        linked_test_runs = [
            TestRunLinkResponse(
                id=tr.id,
                requirement_id=tr.requirement_id,
                test_run_id=tr.test_run_id,
                test_run_name=tr.test_run_name,
                teststation_url=tr.teststation_url,
                status=tr.status,
                created_at=tr.created_at,
            )
            for tr in tr_links
        ]

        tc_count = len(linked_test_cases)
        if tc_count == 0:
            coverage_status = "Uncovered"
        elif tc_count >= 1 and all(
            tc.status in ("Draft",) for tc in linked_test_cases
        ):
            coverage_status = "Partial"
        else:
            coverage_status = "Covered"

        req_resp = RequirementResponse(
            id=req.id,
            project_id=req.project_id,
            parent_id=req.parent_id,
            req_id=req.req_id,
            title=req.title,
            description=req.description,
            status=req.status,
            priority=req.priority,
            req_type=req.req_type,
            created_at=req.created_at,
            updated_at=req.updated_at,
            children=[],
            test_case_count=tc_count,
        )

        items.append(TraceabilityItem(
            requirement=req_resp,
            linked_test_cases=linked_test_cases,
            linked_test_runs=linked_test_runs,
            coverage_status=coverage_status,
        ))

    return items
