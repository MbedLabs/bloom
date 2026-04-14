"""
Test cases API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import TestCase, Project, RequirementTestCase
from app.schemas import TestCaseCreate, TestCaseUpdate, TestCaseResponse

router = APIRouter()


async def _build_test_case_response(tc: TestCase, db: AsyncSession) -> TestCaseResponse:
    req_count_result = await db.execute(
        select(func.count(RequirementTestCase.id)).where(
            RequirementTestCase.test_case_id == tc.id
        )
    )
    req_count = req_count_result.scalar()

    return TestCaseResponse(
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
        requirement_count=req_count,
    )


@router.get("", response_model=list[TestCaseResponse])
async def list_test_cases(
    project_id: int = Query(..., description="Filter by project ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    List test cases for a project.
    """
    result = await db.execute(
        select(TestCase)
        .where(TestCase.project_id == project_id)
        .order_by(TestCase.created_at.desc())
    )
    test_cases = result.scalars().all()

    response = []
    for tc in test_cases:
        resp = await _build_test_case_response(tc, db)
        response.append(resp)

    return response


@router.post("", response_model=TestCaseResponse, status_code=201)
async def create_test_case(
    data: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new test case. Auto-generates tc_id.
    """
    project_result = await db.execute(
        select(Project).where(Project.id == data.project_id)
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    count_result = await db.execute(
        select(func.count(TestCase.id)).where(TestCase.project_id == data.project_id)
    )
    count = count_result.scalar()
    tc_id = f"{project.prefix}-TC-{count + 1:03d}"

    test_case = TestCase(
        project_id=data.project_id,
        tc_id=tc_id,
        title=data.title,
        description=data.description,
        preconditions=data.preconditions,
        steps=data.steps,
        status=data.status,
    )

    db.add(test_case)
    await db.flush()
    await db.refresh(test_case)

    return await _build_test_case_response(test_case, db)


@router.get("/{test_case_id}", response_model=TestCaseResponse)
async def get_test_case(
    test_case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a test case by ID.
    """
    result = await db.execute(
        select(TestCase).where(TestCase.id == test_case_id)
    )
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    return await _build_test_case_response(test_case, db)


@router.patch("/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(
    test_case_id: int,
    data: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a test case.
    """
    result = await db.execute(
        select(TestCase).where(TestCase.id == test_case_id)
    )
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    if data.title is not None:
        test_case.title = data.title
    if data.description is not None:
        test_case.description = data.description
    if data.preconditions is not None:
        test_case.preconditions = data.preconditions
    if data.steps is not None:
        test_case.steps = data.steps
    if data.status is not None:
        test_case.status = data.status

    await db.flush()
    await db.refresh(test_case)

    return await _build_test_case_response(test_case, db)


@router.delete("/{test_case_id}", status_code=204)
async def delete_test_case(
    test_case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a test case.
    """
    result = await db.execute(
        select(TestCase).where(TestCase.id == test_case_id)
    )
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    await db.delete(test_case)
