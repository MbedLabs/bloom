"""Test Campaign API endpoints: configurations and traceability scopes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models import (
    Project,
    Requirement,
    RequirementTestCase,
    TestCampaign,
    TestCampaignItem,
    TestCase,
    TestConfiguration,
    TestSuite,
    TestSuiteItem,
)
from app.models.user import User, UserRole
from app.schemas import (
    RequirementSummary,
    SyncResultsRequest,
    SyncResultsResponse,
    TestCampaignCreate,
    TestCampaignDetailResponse,
    TestCampaignItemResponse,
    TestCampaignItemUpdate,
    TestCampaignResponse,
    TestCampaignUpdate,
    TestCaseResponse,
    TestConfigurationCreate,
    TestConfigurationResponse,
    TestConfigurationUpdate,
    TestSuiteSummary,
)

router = APIRouter()
...


@router.post("/{campaign_id}/sync-results", response_model=SyncResultsResponse)
async def sync_results(
    campaign_id: int,
    data: SyncResultsRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Ingest automated test results for a campaign in bulk.
    Matches results to campaign items using the test case ID (tc_id).
    """
    campaign = (
        await db.execute(select(TestCampaign).where(TestCampaign.id == campaign_id))
    ).scalar_one_or_none()

    if not campaign:
        raise HTTPException(404, "Campaign not found")

    # Get all items in this campaign joined with their test cases
    items_result = await db.execute(
        select(TestCampaignItem, TestCase)
        .join(TestCase, TestCampaignItem.test_case_id == TestCase.id)
        .where(TestCampaignItem.campaign_id == campaign_id)
    )

    # Map tc_id to campaign item
    tc_id_to_item = {tc.tc_id: item for item, tc in items_result.all()}

    updated_count = 0
    not_found = []

    for res in data.results:
        item = tc_id_to_item.get(res.tc_id)
        if item:
            item.status = "Executed"
            item.result = res.status
            item.comment = res.comment
            item.executed_at = res.executed_at or datetime.utcnow()
            updated_count += 1
        else:
            not_found.append(res.tc_id)

    await db.commit()

    return SyncResultsResponse(updated=updated_count, not_found=not_found)


@router.post("/sync-results", response_model=SyncResultsResponse)
async def sync_results_global(
    data: SyncResultsRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Ingest automated test results across all campaigns.
    Matches results to campaign items by tc_id without requiring a specific campaign.
    Used by Bud backend for direct Bud→Bloom result synchronization.
    """
    tc_ids = [r.tc_id for r in data.results]

    items_result = await db.execute(
        select(TestCampaignItem, TestCase)
        .join(TestCase, TestCampaignItem.test_case_id == TestCase.id)
        .where(TestCase.tc_id.in_(tc_ids))
    )

    tc_id_to_item = {tc.tc_id: (item, tc) for item, tc in items_result.all()}

    updated_count = 0
    not_found = []

    for res in data.results:
        match = tc_id_to_item.get(res.tc_id)
        if match:
            item, _ = match
            item.status = "Executed"
            item.result = res.status
            item.comment = res.comment
            item.executed_at = res.executed_at or datetime.utcnow()
            updated_count += 1
        else:
            not_found.append(res.tc_id)

    await db.commit()

    return SyncResultsResponse(updated=updated_count, not_found=not_found)


# ==================== Configurations ====================


@router.get("/configurations", response_model=list[TestConfigurationResponse])
async def list_configurations(
    project_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TestConfiguration)
        .where(TestConfiguration.project_id == project_id)
        .order_by(TestConfiguration.created_at.desc())
    )
    return result.scalars().all()


@router.post("/configurations", response_model=TestConfigurationResponse, status_code=201)
async def create_configuration(
    data: TestConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    proj = await db.execute(select(Project).where(Project.id == data.project_id))
    if not proj.scalar_one_or_none():
        raise HTTPException(404, "Project not found")

    config = TestConfiguration(
        project_id=data.project_id,
        name=data.name,
        description=data.description,
        environment=data.environment,
        parameters=data.parameters,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return config


@router.patch("/configurations/{config_id}", response_model=TestConfigurationResponse)
async def update_configuration(
    config_id: int,
    data: TestConfigurationUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(TestConfiguration).where(TestConfiguration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "Configuration not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    await db.flush()
    await db.refresh(config)
    return config


@router.delete("/configurations/{config_id}", status_code=204)
async def delete_configuration(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(TestConfiguration).where(TestConfiguration.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(404, "Configuration not found")
    await db.delete(config)


# ==================== Campaigns ====================


@router.get("", response_model=list[TestCampaignResponse])
async def list_campaigns(
    project_id: int = Query(...),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    query = select(TestCampaign).where(TestCampaign.project_id == project_id)
    if status:
        query = query.where(TestCampaign.status == status)
    query = query.order_by(TestCampaign.created_at.desc())
    result = await db.execute(query)
    campaigns = result.scalars().all()

    responses = []
    for c in campaigns:
        resp = await _build_campaign_response(c, db)
        responses.append(resp)
    return responses


@router.post("", response_model=TestCampaignDetailResponse, status_code=201)
async def create_campaign(
    data: TestCampaignCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    proj = await db.execute(select(Project).where(Project.id == data.project_id))
    if not proj.scalar_one_or_none():
        raise HTTPException(404, "Project not found")

    suite = None
    if data.suite_id is not None:
        suite = (
            await db.execute(select(TestSuite).where(TestSuite.id == data.suite_id))
        ).scalar_one_or_none()
        if not suite or suite.project_id != data.project_id:
            raise HTTPException(404, "Suite not found")

    if data.configuration_id is not None:
        config = (
            await db.execute(
                select(TestConfiguration).where(TestConfiguration.id == data.configuration_id)
            )
        ).scalar_one_or_none()
        if not config or config.project_id != data.project_id:
            raise HTTPException(404, "Configuration not found")

    campaign = TestCampaign(
        project_id=data.project_id,
        name=data.name,
        description=data.description,
        configuration_id=data.configuration_id,
        suite_id=data.suite_id,
        bud_run_id=data.bud_run_id,
        bud_run_url=data.bud_run_url,
        bud_run_status=data.bud_run_status,
        status=data.status or "Planned",
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)

    selected_test_case_ids = list(data.test_case_ids)
    if suite is not None:
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
        selected_test_case_ids = [item.test_case_id for item in suite_items]

    for tc_id in selected_test_case_ids:
        tc_result = await db.execute(select(TestCase).where(TestCase.id == tc_id))
        tc = tc_result.scalar_one_or_none()
        if tc and tc.project_id == data.project_id:
            item = TestCampaignItem(
                campaign_id=campaign.id,
                test_case_id=tc_id,
                status="Pending",
            )
            db.add(item)

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
    if data.configuration_id is not None:
        if data.configuration_id:
            config = (
                await db.execute(
                    select(TestConfiguration).where(TestConfiguration.id == data.configuration_id)
                )
            ).scalar_one_or_none()
            if not config or config.project_id != campaign.project_id:
                raise HTTPException(404, "Configuration not found")
        campaign.configuration_id = data.configuration_id
    if data.suite_id is not None:
        suite = (
            await db.execute(select(TestSuite).where(TestSuite.id == data.suite_id))
        ).scalar_one_or_none()
        if not suite or suite.project_id != campaign.project_id:
            raise HTTPException(404, "Suite not found")
        campaign.suite_id = data.suite_id
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

    config_resp = None
    suite_resp = None
    if campaign.configuration_id:
        cfg_result = await db.execute(
            select(TestConfiguration).where(TestConfiguration.id == campaign.configuration_id)
        )
        cfg = cfg_result.scalar_one_or_none()
        if cfg:
            config_resp = TestConfigurationResponse(
                id=cfg.id,
                project_id=cfg.project_id,
                name=cfg.name,
                description=cfg.description,
                environment=cfg.environment,
                parameters=cfg.parameters,
                created_at=cfg.created_at,
                updated_at=cfg.updated_at,
            )
    if campaign.suite_id:
        suite = (
            await db.execute(select(TestSuite).where(TestSuite.id == campaign.suite_id))
        ).scalar_one_or_none()
        if suite:
            suite_resp = TestSuiteSummary(
                id=suite.id,
                suite_id=suite.suite_id,
                name=suite.name,
                status=suite.status,
            )

    return TestCampaignResponse(
        id=campaign.id,
        project_id=campaign.project_id,
        configuration_id=campaign.configuration_id,
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
        configuration=config_resp,
        suite=suite_resp,
    )


async def _build_campaign_detail(
    campaign: TestCampaign, db: AsyncSession
) -> TestCampaignDetailResponse:
    base = await _build_campaign_response(campaign, db)

    items_result = await db.execute(
        select(TestCampaignItem).where(TestCampaignItem.campaign_id == campaign.id)
    )
    items = items_result.scalars().all()

    item_responses = []
    requirement_ids = set()
    for item in items:
        tc_result = await db.execute(select(TestCase).where(TestCase.id == item.test_case_id))
        tc = tc_result.scalar_one_or_none()
        tc_resp = None
        if tc:
            tc_resp = await _build_test_case_response(tc, db)
            requirement_ids.update(req.id for req in tc_resp.linked_requirements)
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

    return TestCampaignDetailResponse(
        **base.model_dump(),
        items=item_responses,
        related_requirements=related_requirements,
    )


async def _build_test_case_response(tc: TestCase, db: AsyncSession) -> TestCaseResponse:
    req_links = (
        (
            await db.execute(
                select(RequirementTestCase).where(RequirementTestCase.test_case_id == tc.id)
            )
        )
        .scalars()
        .all()
    )
    linked_requirements = []
    for link in req_links:
        req = (
            await db.execute(select(Requirement).where(Requirement.id == link.requirement_id))
        ).scalar_one_or_none()
        if req:
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
