"""
Test cases API endpoints.
"""

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import get_verified_requirement_links_for_test_case
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_role
from app.models import (
    Project,
    Requirement,
    TestCampaign,
    TestCampaignItem,
    TestCase,
    TestSuite,
    TestSuiteItem,
)
from app.models.user import User
from app.models.user import User as UserModel
from app.models.user import UserRole
from app.schemas import (
    RequirementSummary,
    TestCampaignSummary,
    TestCaseCreate,
    TestCaseResponse,
    TestCaseUpdate,
    TestCaseVerifiesLinkResponse,
    TestSuiteSummary,
)

router = APIRouter()


def _normalize_datetime(value):
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _build_requirement_summary(req: Requirement) -> RequirementSummary:
    return RequirementSummary(id=req.id, req_id=req.req_id, title=req.title, status=req.status)


async def _build_test_case_response(tc: TestCase, db: AsyncSession) -> TestCaseResponse:
    link_rows = await get_verified_requirement_links_for_test_case(tc.id, db)
    req_count = len(link_rows)

    verifies = []
    linked_requirements = []
    for link, req in link_rows:
        req_summary = _build_requirement_summary(req)
        linked_requirements.append(req_summary)
        verifies.append(
            TestCaseVerifiesLinkResponse(
                id=link.id,
                link_type=link.role,
                created_at=link.created_at,
                requirement=req_summary,
            )
        )

    suite_items = (
        (
            await db.execute(
                select(TestSuiteItem)
                .where(TestSuiteItem.test_case_id == tc.id)
                .order_by(TestSuiteItem.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    suite_memberships = []
    for item in suite_items:
        suite = (
            await db.execute(select(TestSuite).where(TestSuite.id == item.suite_id))
        ).scalar_one_or_none()
        if suite:
            suite_memberships.append(
                TestSuiteSummary(
                    id=suite.id,
                    suite_id=suite.suite_id,
                    name=suite.name,
                    status=suite.status,
                )
            )

    campaign_items = (
        (
            await db.execute(
                select(TestCampaignItem)
                .where(TestCampaignItem.test_case_id == tc.id)
                .order_by(TestCampaignItem.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    campaign_memberships = []
    seen_campaign_ids = set()
    for item in campaign_items:
        campaign = (
            await db.execute(select(TestCampaign).where(TestCampaign.id == item.campaign_id))
        ).scalar_one_or_none()
        if campaign and campaign.id not in seen_campaign_ids:
            seen_campaign_ids.add(campaign.id)
            campaign_memberships.append(
                TestCampaignSummary(id=campaign.id, name=campaign.name, status=campaign.status)
            )

    return TestCaseResponse(
        id=tc.id,
        project_id=tc.project_id,
        tc_id=tc.tc_id,
        title=tc.title,
        description=tc.description,
        preconditions=tc.preconditions,
        steps=tc.steps,
        status=tc.status,
        reviewer_id=tc.reviewer_id,
        approver_id=tc.approver_id,
        reviewed_by_id=tc.reviewed_by_id,
        approved_by_id=tc.approved_by_id,
        reviewed_at=tc.reviewed_at,
        approved_at=tc.approved_at,
        created_at=tc.created_at,
        updated_at=tc.updated_at,
        requirement_count=req_count,
        linked_requirements=linked_requirements,
        verifies=verifies,
        suite_memberships=suite_memberships,
        campaign_memberships=campaign_memberships,
    )


@router.get("", response_model=list[TestCaseResponse])
async def list_test_cases(
    project_id: int = Query(..., description="Filter by project ID"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
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
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Create a new test case. Auto-generates tc_id.
    """
    project_result = await db.execute(select(Project).where(Project.id == data.project_id))
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tc_id = await next_doc_id(db, TestCase, TestCase.tc_id, data.project_id, project.prefix, "TC")

    test_case = TestCase(
        project_id=data.project_id,
        tc_id=tc_id,
        title=data.title,
        description=data.description,
        preconditions=data.preconditions,
        steps=data.steps,
        status=data.status,
        reviewer_id=data.reviewer_id,
        approver_id=data.approver_id,
    )

    db.add(test_case)
    await db.flush()
    await db.refresh(test_case)

    return await _build_test_case_response(test_case, db)


@router.get("/{test_case_id}", response_model=TestCaseResponse)
async def get_test_case(
    test_case_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    Get a test case by ID.
    """
    result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    return await _build_test_case_response(test_case, db)


@router.patch("/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(
    test_case_id: int,
    data: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Update a test case.
    """
    result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
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
    fields_set = data.model_fields_set

    if "reviewer_id" in fields_set:
        if data.reviewer_id is None:
            test_case.reviewer_id = None
        else:
            reviewer = (
                await db.execute(select(UserModel).where(UserModel.id == data.reviewer_id))
            ).scalar_one_or_none()
            if not reviewer:
                raise HTTPException(status_code=404, detail="Reviewer not found")
            test_case.reviewer_id = data.reviewer_id
    if "approver_id" in fields_set:
        if data.approver_id is None:
            test_case.approver_id = None
        else:
            approver = (
                await db.execute(select(UserModel).where(UserModel.id == data.approver_id))
            ).scalar_one_or_none()
            if not approver:
                raise HTTPException(status_code=404, detail="Approver not found")
            test_case.approver_id = data.approver_id
    if "reviewed_by_id" in fields_set:
        if data.reviewed_by_id is None:
            test_case.reviewed_by_id = None
        else:
            reviewed_by = (
                await db.execute(select(UserModel).where(UserModel.id == data.reviewed_by_id))
            ).scalar_one_or_none()
            if not reviewed_by:
                raise HTTPException(status_code=404, detail="Reviewed-by user not found")
            test_case.reviewed_by_id = data.reviewed_by_id
    if "approved_by_id" in fields_set:
        if data.approved_by_id is None:
            test_case.approved_by_id = None
        else:
            approved_by = (
                await db.execute(select(UserModel).where(UserModel.id == data.approved_by_id))
            ).scalar_one_or_none()
            if not approved_by:
                raise HTTPException(status_code=404, detail="Approved-by user not found")
            test_case.approved_by_id = data.approved_by_id
    if "reviewed_at" in fields_set:
        test_case.reviewed_at = _normalize_datetime(data.reviewed_at)
    if "approved_at" in fields_set:
        test_case.approved_at = _normalize_datetime(data.approved_at)

    await db.flush()
    await db.refresh(test_case)

    return await _build_test_case_response(test_case, db)


@router.delete("/{test_case_id}", status_code=204)
async def delete_test_case(
    test_case_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Delete a test case.
    """
    result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    await db.delete(test_case)
