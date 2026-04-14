"""
Requirements API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.core.database import get_db
from app.models import Requirement, Project, RequirementTestCase, TestCase, TestRunLink
from app.schemas import (
    RequirementCreate,
    RequirementUpdate,
    RequirementResponse,
    RequirementTestCaseCreate,
    RequirementTestCaseResponse,
    TestRunLinkCreate,
    TestRunLinkResponse,
    TestCaseResponse,
)

router = APIRouter()


async def _build_requirement_response(req: Requirement, db: AsyncSession) -> RequirementResponse:
    tc_count_result = await db.execute(
        select(func.count(RequirementTestCase.id)).where(
            RequirementTestCase.requirement_id == req.id
        )
    )
    tc_count = tc_count_result.scalar()

    children_result = await db.execute(
        select(Requirement).where(Requirement.parent_id == req.id)
    )
    children = children_result.scalars().all()

    children_responses = []
    for child in children:
        child_resp = await _build_requirement_response(child, db)
        children_responses.append(child_resp)

    return RequirementResponse(
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
        children=children_responses,
        test_case_count=tc_count,
    )


@router.get("", response_model=list[RequirementResponse])
async def list_requirements(
    project_id: int = Query(..., description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List requirements for a project with optional status filter.
    """
    query = select(Requirement).where(Requirement.project_id == project_id)

    if status:
        query = query.where(Requirement.status == status)

    query = query.order_by(Requirement.created_at.desc())
    result = await db.execute(query)
    requirements = result.scalars().all()

    response = []
    for req in requirements:
        resp = await _build_requirement_response(req, db)
        response.append(resp)

    return response


@router.post("", response_model=RequirementResponse, status_code=201)
async def create_requirement(
    data: RequirementCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new requirement. Auto-generates req_id based on project prefix.
    """
    project_result = await db.execute(
        select(Project).where(Project.id == data.project_id)
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.parent_id is not None:
        parent_result = await db.execute(
            select(Requirement).where(Requirement.id == data.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent requirement not found")

    count_result = await db.execute(
        select(func.count(Requirement.id)).where(Requirement.project_id == data.project_id)
    )
    count = count_result.scalar()
    req_id = f"{project.prefix}-REQ-{count + 1:03d}"

    requirement = Requirement(
        project_id=data.project_id,
        parent_id=data.parent_id,
        req_id=req_id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        req_type=data.req_type,
    )

    db.add(requirement)
    await db.flush()
    await db.refresh(requirement)

    return await _build_requirement_response(requirement, db)


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a requirement by ID, including children and linked test cases.
    """
    result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    return await _build_requirement_response(requirement, db)


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    requirement_id: int,
    data: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a requirement.
    """
    result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    if data.title is not None:
        requirement.title = data.title
    if data.description is not None:
        requirement.description = data.description
    if data.status is not None:
        requirement.status = data.status
    if data.priority is not None:
        requirement.priority = data.priority
    if data.req_type is not None:
        requirement.req_type = data.req_type
    if data.parent_id is not None:
        if data.parent_id == requirement_id:
            raise HTTPException(status_code=400, detail="Requirement cannot be its own parent")
        parent_result = await db.execute(
            select(Requirement).where(Requirement.id == data.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent requirement not found")
        requirement.parent_id = data.parent_id

    await db.flush()
    await db.refresh(requirement)

    return await _build_requirement_response(requirement, db)


@router.delete("/{requirement_id}", status_code=204)
async def delete_requirement(
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a requirement.
    """
    result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = result.scalar_one_or_none()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    await db.delete(requirement)


@router.post(
    "/{requirement_id}/link-testcase",
    response_model=RequirementTestCaseResponse,
    status_code=201,
)
async def link_test_case(
    requirement_id: int,
    data: RequirementTestCaseCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Link a test case to a requirement.
    """
    req_result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = req_result.scalar_one_or_none()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    tc_result = await db.execute(
        select(TestCase).where(TestCase.id == data.test_case_id)
    )
    test_case = tc_result.scalar_one_or_none()
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    existing = await db.execute(
        select(RequirementTestCase).where(
            RequirementTestCase.requirement_id == requirement_id,
            RequirementTestCase.test_case_id == data.test_case_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Test case already linked to this requirement")

    link = RequirementTestCase(
        requirement_id=requirement_id,
        test_case_id=data.test_case_id,
    )

    db.add(link)
    await db.flush()
    await db.refresh(link)

    return link


@router.delete("/{requirement_id}/link-testcase/{test_case_id}", status_code=204)
async def unlink_test_case(
    requirement_id: int,
    test_case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Unlink a test case from a requirement.
    """
    result = await db.execute(
        select(RequirementTestCase).where(
            RequirementTestCase.requirement_id == requirement_id,
            RequirementTestCase.test_case_id == test_case_id,
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    await db.delete(link)


@router.post(
    "/{requirement_id}/link-testrun",
    response_model=TestRunLinkResponse,
    status_code=201,
)
async def link_test_run(
    requirement_id: int,
    data: TestRunLinkCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Link a test run (from the teststation app) to a requirement.
    """
    req_result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = req_result.scalar_one_or_none()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    link = TestRunLink(
        requirement_id=requirement_id,
        test_run_id=data.test_run_id,
        test_run_name=data.test_run_name,
        teststation_url=data.teststation_url,
        status=data.status,
    )

    db.add(link)
    await db.flush()
    await db.refresh(link)

    return link


@router.get(
    "/{requirement_id}/test-runs",
    response_model=list[TestRunLinkResponse],
)
async def get_linked_test_runs(
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all test runs linked to a requirement.
    """
    req_result = await db.execute(
        select(Requirement).where(Requirement.id == requirement_id)
    )
    requirement = req_result.scalar_one_or_none()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    result = await db.execute(
        select(TestRunLink)
        .where(TestRunLink.requirement_id == requirement_id)
        .order_by(TestRunLink.created_at.desc())
    )
    links = result.scalars().all()

    return links
