"""
Requirements API endpoints.
"""

from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    assignee_can_sign,
    audit_visibility_change,
    check_assignee,
    check_assignees_keep_sight,
    check_create_status_right,
    check_external_change,
    check_status_right,
    check_visibility_right,
    delete_project_row,
    external_create_values,
    get_row_or_404,
    get_visible_row,
    log_artefact_activity,
    log_document_workflow_activity_from_patch,
    page_of,
    prepare_workflow_update,
    requirement_origin_visibility,
    should_log_generic_document_update,
    test_case_summary,
    type_visible,
    updated_summary,
    visible_types,
)
from app.api.link_read_utils import (
    VERIFY_LINK_ROLE,
    VERIFY_SOURCE_TYPE,
    VERIFY_TARGET_TYPE,
    get_verifying_test_case_links_for_requirement,
    verify_link_counts,
)
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import (
    apply_external_visibility_filter,
    get_current_user,
    require_project_access,
)
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
from app.schemas import (
    PaginatedResponse,
    RequirementCreate,
    RequirementResponse,
    RequirementUpdate,
    RequirementVerifiedByLinkResponse,
    TestCampaignSummary,
    TestRunLinkCreate,
    TestRunLinkResponse,
    TestSuiteSummary,
)
from app.services.artefact_tags import attach_tags, creation_tags
from app.services.notification_service import notify_assignment
from app.services.tag_links import sync_tag_links

router = APIRouter()


async def _get_verified_by(
    req_id: int,
    db: AsyncSession,
    current_user: User | None = None,
) -> list[RequirementVerifiedByLinkResponse]:
    link_rows = await get_verifying_test_case_links_for_requirement(req_id, db, current_user)
    return [
        RequirementVerifiedByLinkResponse(
            id=link.id,
            link_type=link.role,
            created_at=link.created_at,
            test_case=test_case_summary(tc),
        )
        for link, tc in link_rows
    ]


class ReqPrefetchContext:
    def __init__(self):
        self.children_by_parent: dict[int, list[Requirement]] = defaultdict(list)
        self.verified_by_by_req: dict[int, list[RequirementVerifiedByLinkResponse]] = defaultdict(
            list
        )
        self.test_run_links_by_req: dict[int, list[TestRunLink]] = defaultdict(list)
        self.tc_suite_summaries: dict[int, list[TestSuiteSummary]] = defaultdict(list)
        self.tc_campaign_summaries: dict[int, list[TestCampaignSummary]] = defaultdict(list)


async def _build_prefetch_context(
    root_req_id: int,
    db: AsyncSession,
    current_user: User | None = None,
) -> ReqPrefetchContext:
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
    if current_user is not None:
        descendants_query = apply_external_visibility_filter(
            descendants_query, req_alias, current_user
        )
    all_reqs = (await db.execute(descendants_query)).scalars().all()
    req_ids = [r.id for r in all_reqs]
    types = (
        await visible_types(db, current_user, all_reqs[0].project_id)
        if current_user is not None and all_reqs
        else None
    )

    for req in all_reqs:
        if req.parent_id is not None:
            ctx.children_by_parent[req.parent_id].append(req)

    # 2. Fetch all verified_by links
    if req_ids:
        verified_by_query = (
            select(ArtefactLink, TestCase)
            .join(TestCase, TestCase.id == ArtefactLink.source_id)
            .where(
                ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
                ArtefactLink.target_type == VERIFY_TARGET_TYPE,
                ArtefactLink.target_id.in_(req_ids),
                ArtefactLink.role == VERIFY_LINK_ROLE,
                type_visible(types, "TC"),
            )
            .order_by(ArtefactLink.created_at.desc(), TestCase.tc_id)
        )
        if current_user is not None:
            verified_by_query = apply_external_visibility_filter(
                verified_by_query, TestCase, current_user
            )
        links_result = await db.execute(verified_by_query)
        all_links = links_result.all()
        for link, tc in all_links:
            ctx.verified_by_by_req[link.target_id].append(
                RequirementVerifiedByLinkResponse(
                    id=link.id,
                    link_type=link.role,
                    created_at=link.created_at,
                    test_case=test_case_summary(tc),
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
        suite_query = (
            select(TestSuiteItem, TestSuite)
            .join(TestSuite, TestSuite.id == TestSuiteItem.suite_id)
            .where(TestSuiteItem.test_case_id.in_(tc_ids), type_visible(types, "TS"))
        )
        if current_user is not None:
            suite_query = apply_external_visibility_filter(suite_query, TestSuite, current_user)
        suite_items_result = await db.execute(suite_query)
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
        campaign_query = (
            select(TestCampaignItem, TestCampaign)
            .join(TestCampaign, TestCampaign.id == TestCampaignItem.campaign_id)
            .where(TestCampaignItem.test_case_id.in_(tc_ids), type_visible(types, "CMP"))
        )
        if current_user is not None:
            campaign_query = apply_external_visibility_filter(
                campaign_query, TestCampaign, current_user
            )
        campaign_items_result = await db.execute(campaign_query)
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
    req: Requirement,
    db: AsyncSession,
    ctx: Optional[ReqPrefetchContext] = None,
    current_user: User | None = None,
) -> RequirementResponse:
    if ctx is None:
        ctx = await _build_prefetch_context(req.id, db, current_user)

    verified_by = ctx.verified_by_by_req.get(req.id, [])
    tc_count = len(verified_by)

    children = ctx.children_by_parent.get(req.id, [])
    children_responses = []
    for child in children:
        child_resp = await _build_requirement_response(child, db, ctx, current_user)
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
        content_json=req.content_json,
        content_html=req.content_html,
        parent_id=req.parent_id,
        req_id=req.req_id,
        title=req.title,
        description=req.description,
        status=req.status,
        visibility=req.visibility,
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
        content_json=req.content_json,
        content_html=req.content_html,
        parent_id=req.parent_id,
        req_id=req.req_id,
        title=req.title,
        description=req.description,
        status=req.status,
        visibility=req.visibility,
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
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    List requirements for a project with optional status filter and pagination.
    """
    await require_project_access(db, current_user, project_id)
    types = await visible_types(db, current_user, project_id)
    if not type_visible(types, "REQ"):
        return PaginatedResponse(items=[], total=0, skip=skip, limit=limit)

    base = select(Requirement).where(Requirement.project_id == project_id)
    base = apply_external_visibility_filter(base, Requirement, current_user)
    if status:
        base = base.where(Requirement.status == status)

    requirements, total = await page_of(db, base, Requirement, skip, limit)
    test_case_counts = (
        await verify_link_counts(
            db,
            ArtefactLink.target_id,
            [req.id for req in requirements],
            other_column=ArtefactLink.source_id,
            other_model=TestCase,
            current_user=current_user,
        )
        if type_visible(types, "TC")
        else {}
    )

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
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new requirement; server assigns req_id.
    """
    project = await get_row_or_404(db, Project, data.project_id, "Project not found")

    await require_project_access(
        db,
        current_user,
        data.project_id,
        permission=("create", "REQ"),
    )
    named = data.model_dump(exclude_unset=True)
    forced = external_create_values(current_user, "REQ", named)
    await check_create_status_right(db, current_user, data.project_id, "REQ", named)
    status = forced.get("status", data.status)
    req_origin = forced.get("req_origin", data.req_origin)

    if data.parent_id is not None:
        parent = await get_visible_row(
            db,
            Requirement,
            data.parent_id,
            "Parent requirement not found",
            current_user,
            permission=("view", "REQ"),
        )
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

    tag_ids = await creation_tags(db, current_user, data.project_id, data.tag_ids)
    requirement = Requirement(
        project_id=data.project_id,
        created_by_id=current_user.id,
        parent_id=data.parent_id,
        req_id=req_id,
        title=data.title,
        description=data.description,
        status=status,
        visibility=requirement_origin_visibility(req_origin),
        priority=data.priority,
        req_type=data.req_type,
        req_origin=req_origin,
        reviewer_id=data.reviewer_id,
        approver_id=data.approver_id,
        content_json=data.content_json,
        content_html=data.content_html,
    )

    db.add(requirement)
    await db.flush()
    await attach_tags(db, "requirement", requirement, tag_ids, current_user)
    await check_assignee(
        db, data.project_id, "REQ", req_id, "review", data.reviewer_id, row=requirement
    )
    await check_assignee(
        db, data.project_id, "REQ", req_id, "approve", data.approver_id, row=requirement
    )
    await db.refresh(requirement)
    await sync_tag_links(
        db,
        project_id=requirement.project_id,
        source_type="REQ",
        source_id=requirement.id,
        content_json=requirement.content_json,
        user=current_user,
    )
    await log_artefact_activity(
        db,
        "requirement",
        requirement.id,
        "created",
        f"{current_user.full_name} created requirement {requirement.req_id}",
    )
    link_path = f"/projects/{project.prefix}/docs/requirements/{requirement.req_id}"
    for assignee_id, role_label in (
        (requirement.reviewer_id, "reviewer"),
        (requirement.approver_id, "approver"),
    ):
        await notify_assignment(
            db,
            assignee_id=assignee_id,
            previous_assignee_id=None,
            role_label=role_label,
            artefact_label=f"requirement {requirement.req_id}",
            project_id=requirement.project_id,
            link_path=link_path,
            actor=current_user,
        )

    return await _build_requirement_response(requirement, db, current_user=current_user)


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    requirement_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Get a requirement by ID, including children and linked test cases.
    """
    requirement = await get_visible_row(
        db,
        Requirement,
        requirement_id,
        "Requirement not found",
        current_user,
        permission=("view", "REQ"),
    )
    response = await _build_requirement_response(requirement, db, current_user=current_user)
    return response.model_copy(
        update={
            "reviewer_can_sign": await assignee_can_sign(
                db, requirement.reviewer_id, requirement.project_id, "REQ", "review", requirement
            ),
            "approver_can_sign": await assignee_can_sign(
                db, requirement.approver_id, requirement.project_id, "REQ", "approve", requirement
            ),
        }
    )


@router.patch("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    requirement_id: int,
    data: RequirementUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Update a requirement.
    """
    requirement = await get_visible_row(
        db,
        Requirement,
        requirement_id,
        "Requirement not found",
        current_user,
        permission=("edit", "REQ"),
    )
    changes = data.model_dump(exclude_unset=True)
    check_external_change(current_user, "REQ", requirement, changes)
    await check_status_right(db, current_user, "REQ", requirement, changes)
    await check_visibility_right(db, current_user, "REQ", requirement, changes)
    for field, step in (("reviewer_id", "review"), ("approver_id", "approve")):
        if changes.get(field) not in (None, getattr(requirement, field, None)):
            await check_assignee(
                db,
                requirement.project_id,
                "REQ",
                requirement.req_id,
                step,
                changes[field],
                row=requirement,
                visibility=(
                    requirement_origin_visibility(changes["req_origin"])
                    if changes.get("req_origin") is not None
                    else None
                ),
            )
    await check_assignees_keep_sight(
        db,
        requirement,
        requirement.req_id,
        (
            requirement_origin_visibility(changes["req_origin"])
            if changes.get("req_origin") is not None
            else None
        ),
    )

    await prepare_workflow_update(db, requirement, data, current_user)

    fields_set = data.model_fields_set
    previous_status = requirement.status if "status" in fields_set else None

    if data.title is not None:
        requirement.title = data.title
    if data.description is not None:
        requirement.description = data.description
    if data.status is not None:
        requirement.status = data.status
    previous_visibility = requirement.visibility
    if data.priority is not None:
        requirement.priority = data.priority
    if data.req_type is not None:
        requirement.req_type = data.req_type
    if data.req_origin is not None:
        requirement.req_origin = data.req_origin
    if data.visibility is not None:
        requirement.visibility = data.visibility
    if data.content_json is not None:
        requirement.content_json = data.content_json
        await sync_tag_links(
            db,
            project_id=requirement.project_id,
            source_type="REQ",
            source_id=requirement.id,
            content_json=data.content_json,
            user=current_user,
        )
    if data.content_html is not None:
        requirement.content_html = data.content_html
    requirement.visibility = requirement_origin_visibility(requirement.req_origin)
    await audit_visibility_change(db, "requirement", requirement, previous_visibility)

    if "parent_id" in fields_set:
        if data.parent_id is None:
            requirement.parent_id = None
        else:
            if data.parent_id == requirement_id:
                raise HTTPException(status_code=400, detail="Requirement cannot be its own parent")
            parent = await get_visible_row(
                db,
                Requirement,
                data.parent_id,
                "Parent requirement not found",
                current_user,
                permission=("view", "REQ"),
            )
            if parent.project_id != requirement.project_id:
                raise HTTPException(
                    status_code=400, detail="Parent requirement must belong to same project"
                )
            requirement.parent_id = data.parent_id
    previous_reviewer_id = requirement.reviewer_id
    previous_approver_id = requirement.approver_id
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

    if (
        requirement.reviewer_id != previous_reviewer_id
        or requirement.approver_id != previous_approver_id
    ):
        prefix = (
            await db.execute(select(Project.prefix).where(Project.id == requirement.project_id))
        ).scalar_one()
        link_path = f"/projects/{prefix}/docs/requirements/{requirement.req_id}"
        for assignee_id, previous_id, role_label in (
            (requirement.reviewer_id, previous_reviewer_id, "reviewer"),
            (requirement.approver_id, previous_approver_id, "approver"),
        ):
            await notify_assignment(
                db,
                assignee_id=assignee_id,
                previous_assignee_id=previous_id,
                role_label=role_label,
                artefact_label=f"requirement {requirement.req_id}",
                project_id=requirement.project_id,
                link_path=link_path,
                actor=current_user,
            )

    return await _build_requirement_response(requirement, db, current_user=current_user)


@router.delete("/{requirement_id}", status_code=204)
async def delete_requirement(
    requirement_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a requirement.
    """
    await delete_project_row(
        db,
        current_user,
        Requirement,
        requirement_id,
        "Requirement not found",
        resource="REQ",
        audit_type="requirement",
        activity=("requirement", "req_id"),
    )


@router.post(
    "/{requirement_id}/link-testrun",
    response_model=TestRunLinkResponse,
    status_code=201,
)
async def link_test_run(
    requirement_id: int,
    data: TestRunLinkCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    _current_user: User = Depends(get_current_user),
):
    """
    Link an externally hosted Bud test run to a requirement.
    """
    await get_visible_row(
        db,
        Requirement,
        requirement_id,
        "Requirement not found",
        _current_user,
        permission=("edit", "REQ"),
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
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Get all test runs linked to a requirement.
    """
    await get_visible_row(
        db,
        Requirement,
        requirement_id,
        "Requirement not found",
        current_user,
        permission=("view", "REQ"),
    )

    result = await db.execute(
        select(TestRunLink)
        .where(TestRunLink.requirement_id == requirement_id)
        .order_by(TestRunLink.created_at.desc())
    )
    links = result.scalars().all()

    return links
