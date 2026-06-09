"""
Requirements API endpoints.
"""

from datetime import timezone
from typing import Optional

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
    get_verifying_test_case_links_for_requirement,
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
    TestRunLink,
    TestSuite,
    TestSuiteItem,
)
from app.models.user import User
from app.models.user import User as UserModel
from app.models.user import UserRole
from app.schemas import (
    PaginatedResponse,
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


from collections import defaultdict


class ReqPrefetchContext:
    def __init__(self):
        self.children_by_parent: dict[int, list[Requirement]] = defaultdict(list)
        self.verified_by_by_req: dict[int, list[RequirementVerifiedByLinkResponse]] = defaultdict(
            list
        )
        self.test_run_links_by_req: dict[int, list[TestRunLink]] = defaultdict(list)
        self.tc_suite_summaries: dict[int, list[TestSuiteSummary]] = defaultdict(list)
        self.tc_campaign_summaries: dict[int, list[TestCampaignSummary]] = defaultdict(list)


async def _build_prefetch_context(root_req_id: int, db: AsyncSession) -> ReqPrefetchContext:
    ctx = ReqPrefetchContext()

    # 1. Fetch all descendants using a recursive CTE
    hierarchy = (
        select(Requirement)
        .where(Requirement.id == root_req_id)
        .cte(name="hierarchy", recursive=True)
    )
    hierarchy = hierarchy.union_all(
        select(Requirement).where(Requirement.parent_id == hierarchy.c.id)
    )
    from sqlalchemy.orm import aliased

    req_alias = aliased(Requirement)
    descendants_query = select(req_alias).join(hierarchy, req_alias.id == hierarchy.c.id)
    all_reqs = (await db.execute(descendants_query)).scalars().all()
    req_ids = [r.id for r in all_reqs]

    for req in all_reqs:
        if req.parent_id is not None:
            ctx.children_by_parent[req.parent_id].append(req)

    # 2. Fetch all verified_by links
    if req_ids:
        links_result = await db.execute(
            select(ArtefactLink, TestCase)
            .join(TestCase, TestCase.id == ArtefactLink.source_id)
            .where(
                ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
                ArtefactLink.target_type == VERIFY_TARGET_TYPE,
                ArtefactLink.target_id.in_(req_ids),
                ArtefactLink.role == VERIFY_LINK_ROLE,
            )
            .order_by(ArtefactLink.created_at.desc(), TestCase.tc_id)
        )
        all_links = links_result.all()
        for link, tc in all_links:
            ctx.verified_by_by_req[link.target_id].append(
                RequirementVerifiedByLinkResponse(
                    id=link.id,
                    link_type=link.role,
                    created_at=link.created_at,
                    test_case=_build_test_case_summary(tc),
                )
            )

        # 3. Fetch all test run links
        tr_links_result = await db.execute(
            select(TestRunLink)
            .where(TestRunLink.requirement_id.in_(req_ids))
            .order_by(TestRunLink.created_at.desc())
        )
        for tr_link in tr_links_result.scalars().all():
            ctx.test_run_links_by_req[tr_link.requirement_id].append(tr_link)

    # 4. Fetch Suite/Campaign backlinks for all involved TestCases
    tc_ids = []
    for links in ctx.verified_by_by_req.values():
        for link in links:
            tc_ids.append(link.test_case.id)

    if tc_ids:
        # Suites
        suite_items_result = await db.execute(
            select(TestSuiteItem, TestSuite)
            .join(TestSuite, TestSuite.id == TestSuiteItem.suite_id)
            .where(TestSuiteItem.test_case_id.in_(tc_ids))
        )
        for item, suite in suite_items_result.all():
            ctx.tc_suite_summaries[item.test_case_id].append(
                TestSuiteSummary(
                    id=suite.id,
                    suite_id=suite.suite_id,
                    name=suite.name,
                    status=suite.status,
                )
            )

        # Campaigns
        campaign_items_result = await db.execute(
            select(TestCampaignItem, TestCampaign)
            .join(TestCampaign, TestCampaign.id == TestCampaignItem.campaign_id)
            .where(TestCampaignItem.test_case_id.in_(tc_ids))
        )
        for item, campaign in campaign_items_result.all():
            ctx.tc_campaign_summaries[item.test_case_id].append(
                TestCampaignSummary(
                    id=campaign.id,
                    campaign_id=campaign.campaign_id or "",
                    name=campaign.name,
                    status=campaign.status,
                )
            )

    return ctx


async def _build_requirement_response(
    req: Requirement, db: AsyncSession, ctx: Optional[ReqPrefetchContext] = None
) -> RequirementResponse:
    if ctx is None:
        ctx = await _build_prefetch_context(req.id, db)

    verified_by = ctx.verified_by_by_req.get(req.id, [])
    tc_count = len(verified_by)

    children = ctx.children_by_parent.get(req.id, [])
    children_responses = []
    for child in children:
        child_resp = await _build_requirement_response(child, db, ctx)
        children_responses.append(child_resp)

    linked_test_runs = ctx.test_run_links_by_req.get(req.id, [])

    suite_backlinks = []
    campaign_backlinks = []
    seen_suite_ids = set()
    seen_campaign_ids = set()

    for link in verified_by:
        tc_id = link.test_case.id
        for suite_summary in ctx.tc_suite_summaries.get(tc_id, []):
            if suite_summary.id not in seen_suite_ids:
                seen_suite_ids.add(suite_summary.id)
                suite_backlinks.append(suite_summary)
        for campaign_summary in ctx.tc_campaign_summaries.get(tc_id, []):
            if campaign_summary.id not in seen_campaign_ids:
                seen_campaign_ids.add(campaign_summary.id)
                campaign_backlinks.append(campaign_summary)

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


def _build_requirement_list_response(
    req: Requirement, test_case_count: int = 0
) -> RequirementResponse:
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
        children=[],
        test_case_count=test_case_count,
        linked_test_cases=[],
        verified_by=[],
        linked_test_runs=[],
        suite_backlinks=[],
        campaign_backlinks=[],
    )


@router.get("", response_model=PaginatedResponse[RequirementResponse])
async def list_requirements(
    project_id: int = Query(..., description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List requirements for a project with optional status filter and pagination.
    """
    await require_project_access(db, current_user, project_id)

    base = select(Requirement).where(Requirement.project_id == project_id)
    if status:
        base = base.where(Requirement.status == status)

    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    query = base.order_by(Requirement.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    requirements = result.scalars().all()
    requirement_ids = [req.id for req in requirements]

    test_case_counts = {req_id: 0 for req_id in requirement_ids}
    if requirement_ids:
        count_rows = (
            await db.execute(
                select(ArtefactLink.target_id, func.count(ArtefactLink.id))
                .where(
                    ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
                    ArtefactLink.target_type == VERIFY_TARGET_TYPE,
                    ArtefactLink.target_id.in_(requirement_ids),
                    ArtefactLink.role == VERIFY_LINK_ROLE,
                )
                .group_by(ArtefactLink.target_id)
            )
        ).all()
        test_case_counts.update({req_id: count for req_id, count in count_rows})

    return PaginatedResponse(
        items=[
            _build_requirement_list_response(req, test_case_counts.get(req.id, 0))
            for req in requirements
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=RequirementResponse, status_code=201)
async def create_requirement(
    data: RequirementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Create a new requirement; server assigns req_id.
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

    if data.parent_id is not None:
        parent_result = await db.execute(
            select(Requirement).where(Requirement.id == data.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent requirement not found")
        if parent.project_id != data.project_id:
            raise HTTPException(
                status_code=400, detail="Parent requirement must belong to same project"
            )

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

    existing = await db.execute(
        select(Requirement).where(
            Requirement.project_id == data.project_id,
            Requirement.req_id == req_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Requirement with this ID already exists")

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
    await log_artefact_activity(
        db,
        "requirement",
        requirement.id,
        "created",
        f"{current_user.full_name} created requirement {requirement.req_id}",
    )

    return await _build_requirement_response(requirement, db)


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a requirement by ID, including children and linked test cases.
    """
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    requirement = result.scalar_one_or_none()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    await require_project_access(db, current_user, requirement.project_id)

    return await _build_requirement_response(requirement, db)


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    requirement_id: int,
    data: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Update a requirement.
    """
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    requirement = result.scalar_one_or_none()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    await require_project_access(
        db,
        current_user,
        requirement.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    fields_set = data.model_fields_set
    previous_status = requirement.status if "status" in fields_set else None

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
            if parent.project_id != requirement.project_id:
                raise HTTPException(
                    status_code=400, detail="Parent requirement must belong to same project"
                )
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
    await log_document_workflow_activity_from_patch(
        db,
        artefact_type="requirement",
        artefact_id=requirement.id,
        public_id=requirement.req_id,
        actor=current_user,
        fields_set=fields_set,
        previous_status=previous_status,
        next_status=requirement.status,
    )
    if should_log_generic_document_update(fields_set):
        await log_artefact_activity(
            db,
            "requirement",
            requirement.id,
            "updated",
            updated_summary(current_user.full_name, "requirement", requirement.req_id, fields_set),
        )

    return await _build_requirement_response(requirement, db)


@router.delete("/{requirement_id}", status_code=204)
async def delete_requirement(
    requirement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Delete a requirement.
    """
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    requirement = result.scalar_one_or_none()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    await require_project_access(
        db,
        current_user,
        requirement.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    await log_artefact_activity(
        db,
        "requirement",
        requirement.id,
        "deleted",
        f"{current_user.full_name} deleted requirement {requirement.req_id}",
    )
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

    await require_project_access(
        db,
        _current_user,
        requirement.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

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
    current_user: User = Depends(get_current_user),
):
    """
    Get all test runs linked to a requirement.
    """
    req_result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    requirement = req_result.scalar_one_or_none()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    await require_project_access(db, current_user, requirement.project_id)

    result = await db.execute(
        select(TestRunLink)
        .where(TestRunLink.requirement_id == requirement_id)
        .order_by(TestRunLink.created_at.desc())
    )
    links = result.scalars().all()

    return links
