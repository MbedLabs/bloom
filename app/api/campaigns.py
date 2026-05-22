"""Test campaign API: traceability scopes and Bud execution linkage."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import get_verified_requirement_links_for_test_case
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_role
from app.models import (
    ArtefactLink,
    CampaignSuite,
    Project,
    Requirement,
    TestCampaign,
    TestCampaignItem,
    TestCase,
    TestConcept,
    TestSuite,
    TestSuiteItem,
)
from app.models.user import User, UserRole
from app.schemas import (
    ArtefactLinkResponse,
    PaginatedResponse,
    RequirementSummary,
    SyncResultsRequest,
    SyncResultsResponse,
    TestCampaignCreate,
    TestCampaignDetailResponse,
    TestCampaignItemResponse,
    TestCampaignItemUpdate,
    TestCampaignResponse,
    TestCampaignSuiteScope,
    TestCampaignUpdate,
    TestCaseResponse,
    TestConceptSummary,
    TestSuiteSummary,
)

router = APIRouter()
...


def _normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)
    return value


def _resolved_execution_time(value: Optional[datetime]) -> datetime:
    resolved = value or datetime.utcnow()
    return _normalize_datetime(resolved) or datetime.utcnow()


def _apply_result_to_test_case(tc: TestCase, res) -> None:
    executed_at = _resolved_execution_time(res.executed_at)
    current = _normalize_datetime(tc.last_executed_at)
    incoming = _normalize_datetime(executed_at)

    if current and incoming and incoming < current:
        return

    tc.last_execution_status = res.status
    tc.last_executed_at = executed_at
    tc.last_execution_comment = res.comment
    if res.bud_run_id is not None:
        tc.last_bud_run_id = res.bud_run_id


def _apply_result_to_campaign_item(item: TestCampaignItem, res) -> None:
    item.status = "Executed"
    item.result = res.status
    item.comment = res.comment
    item.executed_at = _resolved_execution_time(res.executed_at)


@router.post("/sync-results", response_model=SyncResultsResponse)
async def sync_results_global(
    data: SyncResultsRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Ingest automated test results across all campaigns.
    Matches results to campaign items by tc_id. A tc_id can appear in
    multiple campaigns — all matching items are updated.
    """
    tc_ids = [r.tc_id for r in data.results]

    test_cases_result = await db.execute(select(TestCase).where(TestCase.tc_id.in_(tc_ids)))
    tc_id_to_case = {tc.tc_id: tc for tc in test_cases_result.scalars().all()}

    items_result = await db.execute(
        select(TestCampaignItem, TestCase)
        .join(TestCase, TestCampaignItem.test_case_id == TestCase.id)
        .where(TestCase.tc_id.in_(tc_ids))
    )

    tc_id_to_items: dict[str, list] = {}
    for item, tc in items_result.all():
        tc_id_to_items.setdefault(tc.tc_id, []).append(item)

    updated_count = 0
    not_found = []

    for res in data.results:
        tc = tc_id_to_case.get(res.tc_id)
        if not tc:
            not_found.append(res.tc_id)
            continue

        _apply_result_to_test_case(tc, res)

        matched_items = tc_id_to_items.get(res.tc_id, [])
        for item in matched_items:
            _apply_result_to_campaign_item(item, res)

        updated_count += 1

    await db.commit()

    return SyncResultsResponse(updated=updated_count, not_found=not_found)


@router.get("", response_model=PaginatedResponse[TestCampaignResponse])
async def list_campaigns(
    project_id: int = Query(...),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    base = select(TestCampaign).where(TestCampaign.project_id == project_id)
    if status:
        base = base.where(TestCampaign.status == status)

    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    query = base.order_by(TestCampaign.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    campaigns = result.scalars().all()

    return PaginatedResponse(
        items=await _build_campaign_responses_batch(campaigns, db),
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=TestCampaignDetailResponse, status_code=201)
async def create_campaign(
    data: TestCampaignCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    proj_row = await db.execute(select(Project).where(Project.id == data.project_id))
    project = proj_row.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    # Resolve suite_ids: prefer new field, fall back to legacy suite_id
    resolved_suite_ids = list(data.suite_ids) if data.suite_ids else []
    if not resolved_suite_ids and data.suite_id is not None:
        resolved_suite_ids = [data.suite_id]

    # Validate all suites exist and belong to the project
    validated_suites: list[TestSuite] = []
    for sid in resolved_suite_ids:
        suite = (
            await db.execute(select(TestSuite).where(TestSuite.id == sid))
        ).scalar_one_or_none()
        if not suite or suite.project_id != data.project_id:
            raise HTTPException(404, f"Suite {sid} not found")
        validated_suites.append(suite)

    campaign_public_id = await next_doc_id(
        db,
        TestCampaign,
        TestCampaign.campaign_id,
        data.project_id,
        project.prefix,
        "CMP",
    )

    campaign = TestCampaign(
        project_id=data.project_id,
        campaign_id=campaign_public_id,
        name=data.name,
        description=data.description,
        suite_id=resolved_suite_ids[0] if resolved_suite_ids else None,
        bud_run_id=data.bud_run_id,
        bud_run_url=data.bud_run_url,
        bud_run_status=data.bud_run_status,
        status="Planned",
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)

    # Create CampaignSuite rows for multi-suite support
    for suite in validated_suites:
        db.add(CampaignSuite(campaign_id=campaign.id, suite_id=suite.id))

    # Collect test case IDs from all suites (union, dedup)
    selected_test_case_ids: set[int] = set(data.test_case_ids)
    for suite in validated_suites:
        suite_items = (
            (
                await db.execute(
                    select(TestSuiteItem)
                    .where(TestSuiteItem.suite_id == suite.id)
                    .order_by(TestSuiteItem.order, TestSuiteItem.created_at)
                )
            )
            .scalars()
            .all()
        )
        selected_test_case_ids.update(item.test_case_id for item in suite_items)

    if selected_test_case_ids:
        tc_rows = (
            (
                await db.execute(
                    select(TestCase).where(
                        TestCase.id.in_(selected_test_case_ids),
                        TestCase.project_id == data.project_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        for tc in tc_rows:
            db.add(
                TestCampaignItem(
                    campaign_id=campaign.id,
                    test_case_id=tc.id,
                    status="Pending",
                )
            )

    await db.flush()
    await db.refresh(campaign)
    return await _build_campaign_detail(campaign, db)


@router.get("/{campaign_id}", response_model=TestCampaignDetailResponse)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(TestCampaign).where(TestCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    return await _build_campaign_detail(campaign, db)


@router.patch("/{campaign_id}", response_model=TestCampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: TestCampaignUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(TestCampaign).where(TestCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    if data.name is not None:
        campaign.name = data.name
    if data.description is not None:
        campaign.description = data.description
    # Handle suite_ids (multi-suite) or legacy suite_id
    resolved_suite_ids = data.suite_ids
    if resolved_suite_ids is None and data.suite_id is not None:
        resolved_suite_ids = [data.suite_id]
    if resolved_suite_ids is not None:
        for sid in resolved_suite_ids:
            suite = (
                await db.execute(select(TestSuite).where(TestSuite.id == sid))
            ).scalar_one_or_none()
            if not suite or suite.project_id != campaign.project_id:
                raise HTTPException(404, f"Suite {sid} not found")
        # Delete existing CampaignSuite rows
        existing_cs = (
            (
                await db.execute(
                    select(CampaignSuite).where(CampaignSuite.campaign_id == campaign.id)
                )
            )
            .scalars()
            .all()
        )
        for cs in existing_cs:
            await db.delete(cs)
        # Insert new CampaignSuite rows
        for sid in resolved_suite_ids:
            db.add(CampaignSuite(campaign_id=campaign.id, suite_id=sid))
        campaign.suite_id = resolved_suite_ids[0] if resolved_suite_ids else None
    if data.bud_run_id is not None:
        campaign.bud_run_id = data.bud_run_id
    if data.bud_run_url is not None:
        campaign.bud_run_url = data.bud_run_url
    if data.bud_run_status is not None:
        campaign.bud_run_status = data.bud_run_status
    if data.status is not None:
        campaign.status = data.status
    await db.flush()
    await db.refresh(campaign)
    return await _build_campaign_response(campaign, db)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(TestCampaign).where(TestCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    await db.delete(campaign)


@router.get("/{campaign_id}/scope-links", response_model=list[ArtefactLinkResponse])
async def get_campaign_scope_links(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Return all ArtefactLinks involving test cases that belong to this campaign."""
    result = await db.execute(select(TestCampaign).where(TestCampaign.id == campaign_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Campaign not found")

    tc_ids = (
        (
            await db.execute(
                select(TestCampaignItem.test_case_id).where(
                    TestCampaignItem.campaign_id == campaign_id
                )
            )
        )
        .scalars()
        .all()
    )
    if not tc_ids:
        return []

    rows = (
        (
            await db.execute(
                select(ArtefactLink)
                .where(
                    or_(
                        and_(ArtefactLink.source_type == "TC", ArtefactLink.source_id.in_(tc_ids)),
                        and_(ArtefactLink.target_type == "TC", ArtefactLink.target_id.in_(tc_ids)),
                    )
                )
                .order_by(ArtefactLink.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [ArtefactLinkResponse.model_validate(row) for row in rows]


@router.post("/{campaign_id}/items", response_model=TestCampaignItemResponse, status_code=201)
async def add_campaign_item(
    campaign_id: int,
    test_case_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(TestCampaign).where(TestCampaign.id == campaign_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Campaign not found")

    tc_result = await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    if not tc_result.scalar_one_or_none():
        raise HTTPException(404, "Test case not found")

    existing = await db.execute(
        select(TestCampaignItem).where(
            TestCampaignItem.campaign_id == campaign_id,
            TestCampaignItem.test_case_id == test_case_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Test case already in campaign")

    item = TestCampaignItem(
        campaign_id=campaign_id,
        test_case_id=test_case_id,
        status="Pending",
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{campaign_id}/items/{item_id}", status_code=204)
async def remove_campaign_item(
    campaign_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(
        select(TestCampaignItem).where(
            TestCampaignItem.id == item_id,
            TestCampaignItem.campaign_id == campaign_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Campaign item not found")
    await db.delete(item)


@router.patch("/{campaign_id}/items/{item_id}", response_model=TestCampaignItemResponse)
async def update_campaign_item(
    campaign_id: int,
    item_id: int,
    data: TestCampaignItemUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    item = (
        await db.execute(
            select(TestCampaignItem).where(
                TestCampaignItem.id == item_id,
                TestCampaignItem.campaign_id == campaign_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Campaign item not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    await db.refresh(item)

    tc = (
        await db.execute(select(TestCase).where(TestCase.id == item.test_case_id))
    ).scalar_one_or_none()
    tc_resp = await _build_test_case_response(tc, db) if tc else None
    return TestCampaignItemResponse(
        id=item.id,
        campaign_id=item.campaign_id,
        test_case_id=item.test_case_id,
        status=item.status,
        result=item.result,
        comment=item.comment,
        executed_at=item.executed_at,
        created_at=item.created_at,
        test_case=tc_resp,
    )


# ==================== Helpers ====================


async def _build_campaign_responses_batch(
    campaigns: list[TestCampaign], db: AsyncSession
) -> list[TestCampaignResponse]:
    if not campaigns:
        return []

    campaign_ids = [c.id for c in campaigns]
    totals_result = await db.execute(
        select(TestCampaignItem.campaign_id, func.count(TestCampaignItem.id))
        .where(TestCampaignItem.campaign_id.in_(campaign_ids))
        .group_by(TestCampaignItem.campaign_id)
    )
    totals_by_campaign = {row[0]: row[1] for row in totals_result.all()}

    cs_rows = (
        await db.execute(
            select(CampaignSuite, TestSuite)
            .join(TestSuite, TestSuite.id == CampaignSuite.suite_id)
            .where(CampaignSuite.campaign_id.in_(campaign_ids))
            .order_by(CampaignSuite.campaign_id, CampaignSuite.id)
        )
    ).all()
    suites_by_campaign: dict[int, list[TestSuiteSummary]] = {cid: [] for cid in campaign_ids}
    for cs, suite in cs_rows:
        if suite:
            suites_by_campaign.setdefault(cs.campaign_id, []).append(
                TestSuiteSummary(
                    id=suite.id, suite_id=suite.suite_id, name=suite.name, status=suite.status
                )
            )

    responses: list[TestCampaignResponse] = []
    for campaign in campaigns:
        total = totals_by_campaign.get(campaign.id, 0)
        suites_list = suites_by_campaign.get(campaign.id, [])
        suite_resp = suites_list[0] if suites_list else None
        public_id = campaign.campaign_id or ""
        if not public_id:
            raise ValueError(
                f"Campaign {campaign.id} missing campaign_id; ensure startup backfill ran"
            )
        responses.append(
            TestCampaignResponse(
                id=campaign.id,
                project_id=campaign.project_id,
                campaign_id=public_id,
                suite_id=campaign.suite_id,
                bud_run_id=campaign.bud_run_id,
                bud_run_url=campaign.bud_run_url,
                bud_run_status=campaign.bud_run_status,
                name=campaign.name,
                description=campaign.description,
                status=campaign.status,
                started_at=campaign.started_at,
                completed_at=campaign.completed_at,
                created_at=campaign.created_at,
                updated_at=campaign.updated_at,
                total_items=total,
                passed=0,
                failed=0,
                blocked=0,
                pending=total,
                suite=suite_resp,
                suites=suites_list,
            )
        )
    return responses


async def _build_campaign_response(
    campaign: TestCampaign, db: AsyncSession
) -> TestCampaignResponse:
    total = (
        await db.execute(
            select(func.count(TestCampaignItem.id)).where(
                TestCampaignItem.campaign_id == campaign.id
            )
        )
    ).scalar() or 0

    # Build suites list from CampaignSuite join table
    cs_rows = (
        await db.execute(
            select(CampaignSuite, TestSuite)
            .join(TestSuite, TestSuite.id == CampaignSuite.suite_id)
            .where(CampaignSuite.campaign_id == campaign.id)
            .order_by(CampaignSuite.id)
        )
    ).all()
    suites_list: list[TestSuiteSummary] = []
    for _cs, suite in cs_rows:
        if suite:
            suites_list.append(
                TestSuiteSummary(
                    id=suite.id, suite_id=suite.suite_id, name=suite.name, status=suite.status
                )
            )

    # Legacy single-suite field: first suite or direct FK
    suite_resp = suites_list[0] if suites_list else None
    public_id = campaign.campaign_id or ""
    if not public_id:
        raise ValueError(f"Campaign {campaign.id} missing campaign_id; ensure startup backfill ran")

    return TestCampaignResponse(
        id=campaign.id,
        project_id=campaign.project_id,
        campaign_id=public_id,
        suite_id=campaign.suite_id,
        bud_run_id=campaign.bud_run_id,
        bud_run_url=campaign.bud_run_url,
        bud_run_status=campaign.bud_run_status,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        total_items=total,
        passed=0,
        failed=0,
        blocked=0,
        pending=total,
        suite=suite_resp,
        suites=suites_list,
    )


async def _build_campaign_detail(
    campaign: TestCampaign, db: AsyncSession
) -> TestCampaignDetailResponse:
    base = await _build_campaign_response(campaign, db)

    items_result = await db.execute(
        select(TestCampaignItem).where(TestCampaignItem.campaign_id == campaign.id)
    )
    items = items_result.scalars().all()

    # Pre-fetch all TestCases for these items
    tc_ids = [item.test_case_id for item in items]
    test_cases_map = {}
    if tc_ids:
        tc_result = await db.execute(select(TestCase).where(TestCase.id.in_(tc_ids)))
        test_cases_map = {tc.id: tc for tc in tc_result.scalars().all()}

    # Pre-fetch all requirement links for these TestCases
    linked_reqs_by_tc: dict[int, list[RequirementSummary]] = {}
    requirement_ids = set()
    if tc_ids:
        links_result = await db.execute(
            select(ArtefactLink, Requirement)
            .join(Requirement, Requirement.id == ArtefactLink.target_id)
            .where(
                ArtefactLink.source_type == "TC",
                ArtefactLink.target_type == "REQ",
                ArtefactLink.source_id.in_(tc_ids),
                ArtefactLink.role == "verifies",
            )
            .order_by(ArtefactLink.created_at.desc(), Requirement.req_id)
        )
        for link, req in links_result.all():
            summary = RequirementSummary(
                id=req.id, req_id=req.req_id, title=req.title, status=req.status
            )
            linked_reqs_by_tc.setdefault(link.source_id, []).append(summary)
            requirement_ids.add(req.id)

    item_responses = []
    for item in items:
        tc = test_cases_map.get(item.test_case_id)
        tc_resp = None
        if tc:
            linked_requirements = linked_reqs_by_tc.get(tc.id, [])
            tc_resp = TestCaseResponse(
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
                requirement_count=len(linked_requirements),
                linked_requirements=linked_requirements,
                verifies=[],
                suite_memberships=[],
            )

        item_responses.append(
            TestCampaignItemResponse(
                id=item.id,
                campaign_id=item.campaign_id,
                test_case_id=item.test_case_id,
                status=item.status,
                result=item.result,
                comment=item.comment,
                executed_at=item.executed_at,
                created_at=item.created_at,
                test_case=tc_resp,
            )
        )

    related_requirements = []
    if requirement_ids:
        reqs = (
            (
                await db.execute(
                    select(Requirement)
                    .where(Requirement.id.in_(requirement_ids))
                    .order_by(Requirement.req_id)
                )
            )
            .scalars()
            .all()
        )
        related_requirements = [
            RequirementSummary(id=req.id, req_id=req.req_id, title=req.title, status=req.status)
            for req in reqs
        ]

    # Related concepts: find CPTs linked to any TC in the campaign via ArtefactLink
    tc_ids = [item.test_case_id for item in items]
    related_concepts: list[TestConceptSummary] = []
    if tc_ids:
        concept_links = (
            (
                await db.execute(
                    select(ArtefactLink.source_id)
                    .where(
                        ArtefactLink.source_type == "CPT",
                        ArtefactLink.target_type == "TC",
                        ArtefactLink.target_id.in_(tc_ids),
                    )
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
        if concept_links:
            concepts = (
                (await db.execute(select(TestConcept).where(TestConcept.id.in_(concept_links))))
                .scalars()
                .all()
            )
            related_concepts = [
                TestConceptSummary(id=c.id, concept_id=c.concept_id, name=c.name, status=c.status)
                for c in concepts
            ]

    # Build suite_scopes: group campaign items under their linked suites
    item_by_tc_id: dict[int, TestCampaignItemResponse] = {
        ir.test_case_id: ir for ir in item_responses
    }
    claimed_tc_ids: set[int] = set()
    suite_scopes: list[TestCampaignSuiteScope] = []

    suite_items_result = await db.execute(
        select(TestSuiteItem, TestSuite)
        .join(TestSuite, TestSuite.id == TestSuiteItem.suite_id)
        .join(CampaignSuite, CampaignSuite.suite_id == TestSuite.id)
        .where(CampaignSuite.campaign_id == campaign.id)
    )

    suite_tc_ids_map: dict[int, set[int]] = {}
    suite_by_id: dict[int, TestSuite] = {}

    for si, suite in suite_items_result.all():
        suite_by_id[suite.id] = suite
        suite_tc_ids_map.setdefault(suite.id, set()).add(si.test_case_id)

    for suite_id, suite in suite_by_id.items():
        suite_tc_ids = suite_tc_ids_map[suite_id]
        scope_items = [item_by_tc_id[tc_id] for tc_id in suite_tc_ids if tc_id in item_by_tc_id]
        claimed_tc_ids.update(tc_id for tc_id in suite_tc_ids if tc_id in item_by_tc_id)

        suite_scopes.append(
            TestCampaignSuiteScope(
                suite=TestSuiteSummary(
                    id=suite.id, suite_id=suite.suite_id, name=suite.name, status=suite.status
                ),
                items=scope_items,
            )
        )

    ad_hoc_items = [ir for ir in item_responses if ir.test_case_id not in claimed_tc_ids]

    return TestCampaignDetailResponse(
        **base.model_dump(),
        items=item_responses,
        suite_scopes=suite_scopes,
        ad_hoc_items=ad_hoc_items,
        related_requirements=related_requirements,
        related_concepts=related_concepts,
    )


async def _build_test_case_response(tc: TestCase, db: AsyncSession) -> TestCaseResponse:
    linked_requirements = []
    for _link, req in await get_verified_requirement_links_for_test_case(tc.id, db):
        linked_requirements.append(
            RequirementSummary(id=req.id, req_id=req.req_id, title=req.title, status=req.status)
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
        created_at=tc.created_at,
        updated_at=tc.updated_at,
        requirement_count=len(linked_requirements),
        linked_requirements=linked_requirements,
        verifies=[],
        suite_memberships=[],
    )
