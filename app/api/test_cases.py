"""
Test cases API endpoints.
"""

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    log_artefact_activity,
    log_document_workflow_activity_from_patch,
    should_log_generic_document_update,
    updated_summary,
)
from app.api.link_read_utils import (
    VERIFY_LINK_ROLE,
    VERIFY_SOURCE_TYPE,
    VERIFY_TARGET_TYPE,
    get_verified_requirement_links_for_test_case,
)
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_project_access, require_role
from app.models import (
    ArtefactLink,
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
    PaginatedResponse,
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

    suite_items_result = await db.execute(
        select(TestSuiteItem, TestSuite)
        .join(TestSuite, TestSuite.id == TestSuiteItem.suite_id)
        .where(TestSuiteItem.test_case_id == tc.id)
        .order_by(TestSuiteItem.created_at.desc())
    )
    suite_memberships = []
    seen_suite_ids: set[int] = set()
    for item, suite in suite_items_result.all():
        if suite.id not in seen_suite_ids:
            seen_suite_ids.add(suite.id)
            suite_memberships.append(
                TestSuiteSummary(
                    id=suite.id,
                    suite_id=suite.suite_id,
                    name=suite.name,
                    status=suite.status,
                )
            )

    campaign_items_result = await db.execute(
        select(TestCampaignItem, TestCampaign)
        .join(TestCampaign, TestCampaign.id == TestCampaignItem.campaign_id)
        .where(TestCampaignItem.test_case_id == tc.id)
        .order_by(TestCampaignItem.created_at.desc())
    )
    campaign_memberships = []
    seen_campaign_ids: set[int] = set()
    for item, campaign in campaign_items_result.all():
        if campaign.id not in seen_campaign_ids:
            seen_campaign_ids.add(campaign.id)
            campaign_memberships.append(
                TestCampaignSummary(
                    id=campaign.id,
                    campaign_id=campaign.campaign_id or "",
                    name=campaign.name,
                    status=campaign.status,
                )
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
        last_execution_status=tc.last_execution_status,
        last_executed_at=tc.last_executed_at,
        last_execution_comment=tc.last_execution_comment,
        last_bud_run_id=tc.last_bud_run_id,
        created_at=tc.created_at,
        updated_at=tc.updated_at,
        requirement_count=req_count,
        linked_requirements=linked_requirements,
        verifies=verifies,
        suite_memberships=suite_memberships,
        campaign_memberships=campaign_memberships,
    )


def _build_test_case_list_response(tc: TestCase, requirement_count: int = 0) -> TestCaseResponse:
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
        last_execution_status=tc.last_execution_status,
        last_executed_at=tc.last_executed_at,
        last_execution_comment=tc.last_execution_comment,
        last_bud_run_id=tc.last_bud_run_id,
        created_at=tc.created_at,
        updated_at=tc.updated_at,
        requirement_count=requirement_count,
        linked_requirements=[],
        verifies=[],
        suite_memberships=[],
        campaign_memberships=[],
    )


@router.get("", response_model=PaginatedResponse[TestCaseResponse])
async def list_test_cases(
    project_id: int = Query(..., description="Filter by project ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List test cases for a project with pagination.
    """
    await require_project_access(db, current_user, project_id)

    base = select(TestCase).where(TestCase.project_id == project_id)
    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    query = base.order_by(TestCase.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    test_cases = result.scalars().all()
    test_case_ids = [tc.id for tc in test_cases]

    requirement_counts = {tc_id: 0 for tc_id in test_case_ids}
    if test_case_ids:
        count_rows = (
            await db.execute(
                select(ArtefactLink.source_id, func.count(ArtefactLink.id))
                .where(
                    ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
                    ArtefactLink.target_type == VERIFY_TARGET_TYPE,
                    ArtefactLink.source_id.in_(test_case_ids),
                    ArtefactLink.role == VERIFY_LINK_ROLE,
                )
                .group_by(ArtefactLink.source_id)
            )
        ).all()
        requirement_counts.update({tc_id: count for tc_id, count in count_rows})

    return PaginatedResponse(
        items=[
            _build_test_case_list_response(tc, requirement_counts.get(tc.id, 0))
            for tc in test_cases
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=TestCaseResponse, status_code=201)
async def create_test_case(
    data: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Create a new test case; server assigns tc_id.
    """
    project_result = await db.execute(select(Project).where(Project.id == data.project_id))
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await require_project_access(
        db,
        current_user,
        data.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    tc_id = await next_doc_id(db, TestCase, TestCase.tc_id, data.project_id, project.prefix, "TC")

    existing = await db.execute(
        select(TestCase).where(
            TestCase.project_id == data.project_id,
            TestCase.tc_id == tc_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Test case with this ID already exists")

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
    await log_artefact_activity(
        db,
        "test-case",
        test_case.id,
        "created",
        f"{current_user.full_name} created test case {test_case.tc_id}",
    )

    return await _build_test_case_response(test_case, db)


@router.get("/{test_case_id}", response_model=TestCaseResponse)
async def get_test_case(
    test_case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a test case by ID.
    """
    result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    await require_project_access(db, current_user, test_case.project_id)

    return await _build_test_case_response(test_case, db)


@router.patch("/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(
    test_case_id: int,
    data: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Update a test case.
    """
    result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    await require_project_access(
        db,
        current_user,
        test_case.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    fields_set = data.model_fields_set
    previous_status = test_case.status if "status" in fields_set else None

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
    await log_document_workflow_activity_from_patch(
        db,
        artefact_type="test-case",
        artefact_id=test_case.id,
        public_id=test_case.tc_id,
        actor=current_user,
        fields_set=fields_set,
        previous_status=previous_status,
        next_status=test_case.status,
    )
    if should_log_generic_document_update(fields_set):
        await log_artefact_activity(
            db,
            "test-case",
            test_case.id,
            "updated",
            updated_summary(current_user.full_name, "test case", test_case.tc_id, fields_set),
        )

    return await _build_test_case_response(test_case, db)


@router.delete("/{test_case_id}", status_code=204)
async def delete_test_case(
    test_case_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Delete a test case.
    """
    result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    await require_project_access(
        db,
        current_user,
        test_case.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    await log_artefact_activity(
        db,
        "test-case",
        test_case.id,
        "deleted",
        f"{current_user.full_name} deleted test case {test_case.tc_id}",
    )
    await db.delete(test_case)
