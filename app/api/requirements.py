"""
Requirements API endpoints.
"""

from datetime import timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import get_verifying_test_case_links_for_requirement
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_role
from app.models import (
    Project,
    Requirement,
    TestCampaign,
    TestCampaignItem,
    TestCase,
    TestRunLink,
    TestSuite,
    TestSuiteItem,
)
from app.models.user import User
from app.models.user import User as UserModel
from app.models.user import UserRole
from app.schemas import (
    RequirementCreate,
    RequirementResponse,
    RequirementUpdate,
    RequirementVerifiedByLinkResponse,
    TestCampaignSummary,
    TestCaseSummary,
    TestRunLinkCreate,
    TestRunLinkResponse,
    TestSuiteSummary,
)

router = APIRouter()


def _normalize_datetime(value):
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _build_test_case_summary(tc: TestCase) -> TestCaseSummary:
    return TestCaseSummary(id=tc.id, tc_id=tc.tc_id, title=tc.title, status=tc.status)


async def _get_verified_by(
    req_id: int, db: AsyncSession
) -> list[RequirementVerifiedByLinkResponse]:
    link_rows = await get_verifying_test_case_links_for_requirement(req_id, db)
    return [
        RequirementVerifiedByLinkResponse(
            id=link.id,
            link_type=link.role,
            created_at=link.created_at,
            test_case=_build_test_case_summary(tc),
        )
        for link, tc in link_rows
    ]


async def _build_requirement_response(req: Requirement, db: AsyncSession) -> RequirementResponse:
    verified_by = await _get_verified_by(req.id, db)
    tc_count = len(verified_by)

    children_result = await db.execute(select(Requirement).where(Requirement.parent_id == req.id))
    children = children_result.scalars().all()

    children_responses = []
    for child in children:
        child_resp = await _build_requirement_response(child, db)
        children_responses.append(child_resp)

    linked_test_runs = (
        (
            await db.execute(
                select(TestRunLink)
                .where(TestRunLink.requirement_id == req.id)
                .order_by(TestRunLink.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    linked_tc_ids = [link.test_case.id for link in verified_by]
    suite_backlinks = []
    campaign_backlinks = []
    seen_suite_ids = set()
    seen_campaign_ids = set()
    if linked_tc_ids:
        suite_items = (
            (
                await db.execute(
                    select(TestSuiteItem).where(TestSuiteItem.test_case_id.in_(linked_tc_ids))
                )
            )
            .scalars()
            .all()
        )
        for item in suite_items:
            suite = (
                await db.execute(select(TestSuite).where(TestSuite.id == item.suite_id))
            ).scalar_one_or_none()
            if suite and suite.id not in seen_suite_ids:
                seen_suite_ids.add(suite.id)
                suite_backlinks.append(
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
                    select(TestCampaignItem).where(TestCampaignItem.test_case_id.in_(linked_tc_ids))
                )
            )
            .scalars()
            .all()
        )
        for item in campaign_items:
            campaign = (
                await db.execute(select(TestCampaign).where(TestCampaign.id == item.campaign_id))
            ).scalar_one_or_none()
            if campaign and campaign.id not in seen_campaign_ids:
                seen_campaign_ids.add(campaign.id)
                campaign_backlinks.append(
                    TestCampaignSummary(id=campaign.id, name=campaign.name, status=campaign.status)
                )

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
        req_origin=req.req_origin,
        reviewer_id=req.reviewer_id,
        approver_id=req.approver_id,
        reviewed_by_id=req.reviewed_by_id,
        approved_by_id=req.approved_by_id,
        reviewed_at=req.reviewed_at,
        approved_at=req.approved_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
        children=children_responses,
        test_case_count=tc_count,
        linked_test_cases=[link.test_case for link in verified_by],
        verified_by=verified_by,
        linked_test_runs=[TestRunLinkResponse.model_validate(item) for item in linked_test_runs],
        suite_backlinks=suite_backlinks,
        campaign_backlinks=campaign_backlinks,
    )


@router.get("", response_model=list[RequirementResponse])
async def list_requirements(
    project_id: int = Query(..., description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
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
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Create a new requirement. Auto-generates req_id based on project prefix.
    """
    project_result = await db.execute(select(Project).where(Project.id == data.project_id))
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

    if data.reviewer_id is not None:
        reviewer = (
            await db.execute(select(UserModel).where(UserModel.id == data.reviewer_id))
        ).scalar_one_or_none()
        if not reviewer:
            raise HTTPException(status_code=404, detail="Reviewer not found")

    if data.approver_id is not None:
        approver = (
            await db.execute(select(UserModel).where(UserModel.id == data.approver_id))
        ).scalar_one_or_none()
        if not approver:
            raise HTTPException(status_code=404, detail="Approver not found")

    req_id = await next_doc_id(
        db, Requirement, Requirement.req_id, data.project_id, project.prefix, "REQ"
    )

    requirement = Requirement(
        project_id=data.project_id,
        parent_id=data.parent_id,
        req_id=req_id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        req_type=data.req_type,
        req_origin=data.req_origin,
        reviewer_id=data.reviewer_id,
        approver_id=data.approver_id,
    )

    db.add(requirement)
    await db.flush()
    await db.refresh(requirement)

    return await _build_requirement_response(requirement, db)


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    Get a requirement by ID, including children and linked test cases.
    """
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    requirement = result.scalar_one_or_none()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    return await _build_requirement_response(requirement, db)


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    requirement_id: int,
    data: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Update a requirement.
    """
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
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
    if data.req_origin is not None:
        requirement.req_origin = data.req_origin
    fields_set = data.model_fields_set

    if "parent_id" in fields_set:
        if data.parent_id is None:
            requirement.parent_id = None
        else:
            if data.parent_id == requirement_id:
                raise HTTPException(status_code=400, detail="Requirement cannot be its own parent")
            parent_result = await db.execute(
                select(Requirement).where(Requirement.id == data.parent_id)
            )
            parent = parent_result.scalar_one_or_none()
            if not parent:
                raise HTTPException(status_code=404, detail="Parent requirement not found")
            requirement.parent_id = data.parent_id
    if "reviewer_id" in fields_set:
        if data.reviewer_id is None:
            requirement.reviewer_id = None
        else:
            reviewer = (
                await db.execute(select(UserModel).where(UserModel.id == data.reviewer_id))
            ).scalar_one_or_none()
            if not reviewer:
                raise HTTPException(status_code=404, detail="Reviewer not found")
            requirement.reviewer_id = data.reviewer_id
    if "approver_id" in fields_set:
        if data.approver_id is None:
            requirement.approver_id = None
        else:
            approver = (
                await db.execute(select(UserModel).where(UserModel.id == data.approver_id))
            ).scalar_one_or_none()
            if not approver:
                raise HTTPException(status_code=404, detail="Approver not found")
            requirement.approver_id = data.approver_id
    if "reviewed_by_id" in fields_set:
        if data.reviewed_by_id is None:
            requirement.reviewed_by_id = None
        else:
            reviewed_by = (
                await db.execute(select(UserModel).where(UserModel.id == data.reviewed_by_id))
            ).scalar_one_or_none()
            if not reviewed_by:
                raise HTTPException(status_code=404, detail="Reviewed-by user not found")
            requirement.reviewed_by_id = data.reviewed_by_id
    if "approved_by_id" in fields_set:
        if data.approved_by_id is None:
            requirement.approved_by_id = None
        else:
            approved_by = (
                await db.execute(select(UserModel).where(UserModel.id == data.approved_by_id))
            ).scalar_one_or_none()
            if not approved_by:
                raise HTTPException(status_code=404, detail="Approved-by user not found")
            requirement.approved_by_id = data.approved_by_id
    if "reviewed_at" in fields_set:
        requirement.reviewed_at = _normalize_datetime(data.reviewed_at)
    if "approved_at" in fields_set:
        requirement.approved_at = _normalize_datetime(data.approved_at)

    await db.flush()
    await db.refresh(requirement)

    return await _build_requirement_response(requirement, db)


@router.delete("/{requirement_id}", status_code=204)
async def delete_requirement(
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Delete a requirement.
    """
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    requirement = result.scalar_one_or_none()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    await db.delete(requirement)


@router.post(
    "/{requirement_id}/link-testrun",
    response_model=TestRunLinkResponse,
    status_code=201,
)
async def link_test_run(
    requirement_id: int,
    data: TestRunLinkCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Link a test run (from the teststation app) to a requirement.
    """
    req_result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
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
    _current_user: User = Depends(get_current_user),
):
    """
    Get all test runs linked to a requirement.
    """
    req_result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
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
