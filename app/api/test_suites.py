"""Reusable test suite API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import false, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.artefact_utils import (
    apply_update,
    check_create_status_right,
    check_external_change,
    check_status_right,
    check_visibility_right,
    delete_project_row,
    external_create_values,
    get_row_or_404,
    get_visible_row,
    page_of,
    prepare_workflow_update,
    requirement_summary,
    test_case_summary,
    type_visible,
    visible_types,
)
from app.api.link_read_utils import get_requirement_ids_verified_by_test_cases
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import (
    apply_external_visibility_filter,
    doc_type_visible,
    get_current_user,
    require_project_access,
)
from app.models import (
    ArtefactLink,
    CampaignSuite,
    Project,
    Requirement,
    TestCampaign,
    TestCase,
    TestConcept,
    TestSuite,
    TestSuiteItem,
)
from app.models.user import User
from app.schemas import (
    PaginatedResponse,
    TestCampaignSummary,
    TestConceptSummary,
    TestSuiteCreate,
    TestSuiteDetailResponse,
    TestSuiteItemResponse,
    TestSuiteResponse,
    TestSuiteUpdate,
)
from app.services.artefact_tags import attach_tags, creation_tags
from app.services.document_workflow import prepare_content_write

router = APIRouter()


async def _build_suite_response(
    suite: TestSuite,
    db: AsyncSession,
    current_user: User | None = None,
    tc_visible: bool = True,
) -> TestSuiteResponse:
    total_items_query = (
        select(func.count(TestSuiteItem.id))
        .join(TestCase, TestCase.id == TestSuiteItem.test_case_id)
        .where(TestSuiteItem.suite_id == suite.id)
    )
    if current_user is not None:
        total_items_query = apply_external_visibility_filter(
            total_items_query, TestCase, current_user
        )
    if not tc_visible:
        total_items_query = total_items_query.where(false())
    total_items = (await db.execute(total_items_query)).scalar() or 0
    latest_execution_query = (
        select(
            TestCase.last_execution_status,
            TestCase.last_executed_at,
            TestCase.last_bud_run_id,
        )
        .join(TestSuiteItem, TestSuiteItem.test_case_id == TestCase.id)
        .where(TestSuiteItem.suite_id == suite.id, TestCase.last_executed_at.is_not(None))
        .order_by(TestCase.last_executed_at.desc(), TestCase.id.desc())
        .limit(1)
    )
    if current_user is not None:
        latest_execution_query = apply_external_visibility_filter(
            latest_execution_query, TestCase, current_user
        )
    if not tc_visible:
        latest_execution_query = latest_execution_query.where(false())
    latest_execution = (await db.execute(latest_execution_query)).one_or_none()
    return TestSuiteResponse(
        id=suite.id,
        project_id=suite.project_id,
        suite_id=suite.suite_id,
        name=suite.name,
        description=suite.description,
        status=suite.status,
        visibility=suite.visibility,
        created_at=suite.created_at,
        updated_at=suite.updated_at,
        total_items=total_items,
        last_execution_status=latest_execution[0] if latest_execution else None,
        last_executed_at=latest_execution[1] if latest_execution else None,
        last_bud_run_id=latest_execution[2] if latest_execution else None,
    )


async def _build_suite_detail(
    suite: TestSuite, db: AsyncSession, current_user: User | None = None
) -> TestSuiteDetailResponse:
    types = await visible_types(db, current_user, suite.project_id) if current_user else None
    base = await _build_suite_response(
        suite, db, current_user, tc_visible=type_visible(types, "TC")
    )
    items_query = (
        select(TestSuiteItem, TestCase)
        .join(TestCase, TestCase.id == TestSuiteItem.test_case_id)
        .where(TestSuiteItem.suite_id == suite.id)
        .order_by(TestSuiteItem.order, TestSuiteItem.created_at)
    )
    if current_user is not None:
        items_query = apply_external_visibility_filter(items_query, TestCase, current_user)
    if not type_visible(types, "TC"):
        items_query = items_query.where(false())
    items_result = await db.execute(items_query)

    item_responses = []
    tc_ids = []
    for item, tc in items_result.all():
        item_responses.append(
            TestSuiteItemResponse(
                id=item.id,
                suite_id=item.suite_id,
                test_case_id=item.test_case_id,
                order=item.order,
                created_at=item.created_at,
                test_case=test_case_summary(tc),
            )
        )
        tc_ids.append(tc.id)

    requirement_ids: set[int] = set()
    if tc_ids:
        requirement_ids.update(await get_requirement_ids_verified_by_test_cases(tc_ids, db))

    requirements = []
    if requirement_ids and type_visible(types, "REQ"):
        reqs = (
            (
                await db.execute(
                    apply_external_visibility_filter(
                        select(Requirement)
                        .where(Requirement.id.in_(requirement_ids))
                        .order_by(Requirement.req_id),
                        Requirement,
                        current_user,
                    )
                )
            )
            .scalars()
            .all()
        )
        requirements = [requirement_summary(req) for req in reqs]

    campaigns = (
        (
            await db.execute(
                apply_external_visibility_filter(
                    select(TestCampaign)
                    .join(CampaignSuite, CampaignSuite.campaign_id == TestCampaign.id)
                    .where(CampaignSuite.suite_id == suite.id, type_visible(types, "CMP"))
                    .order_by(TestCampaign.created_at.desc()),
                    TestCampaign,
                    current_user,
                )
            )
        )
        .scalars()
        .all()
    )
    linked_campaigns = [
        TestCampaignSummary(
            id=campaign.id,
            campaign_id=campaign.campaign_id or "",
            name=campaign.name,
            status=campaign.status,
        )
        for campaign in campaigns
    ]

    related_concepts: list[TestConceptSummary] = []
    if tc_ids and type_visible(types, "CPT"):
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
                (
                    await db.execute(
                        apply_external_visibility_filter(
                            select(TestConcept).where(TestConcept.id.in_(concept_links)),
                            TestConcept,
                            current_user,
                        )
                    )
                )
                .scalars()
                .all()
            )
            related_concepts = [
                TestConceptSummary(id=c.id, concept_id=c.concept_id, name=c.name, status=c.status)
                for c in concepts
            ]

    return TestSuiteDetailResponse(
        **base.model_dump(),
        items=item_responses,
        related_requirements=requirements,
        linked_campaigns=linked_campaigns,
        related_concepts=related_concepts,
    )


@router.get("", response_model=PaginatedResponse[TestSuiteResponse])
async def list_suites(
    project_id: int = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    await require_project_access(db, current_user, project_id)
    types = await visible_types(db, current_user, project_id)
    if not type_visible(types, "TS"):
        return PaginatedResponse(items=[], total=0, skip=skip, limit=limit)

    base = select(TestSuite).where(TestSuite.project_id == project_id)
    base = apply_external_visibility_filter(base, TestSuite, current_user)
    suites, total = await page_of(db, base, TestSuite, skip, limit)
    tc_visible = type_visible(types, "TC")

    return PaginatedResponse(
        items=[
            await _build_suite_response(item, db, current_user, tc_visible=tc_visible)
            for item in suites
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=TestSuiteDetailResponse, status_code=201)
async def create_suite(
    data: TestSuiteCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Create a test suite. test_case_ids that are missing or belong to another project are skipped."""
    project = await get_row_or_404(db, Project, data.project_id, "Project not found")

    await require_project_access(
        db,
        current_user,
        data.project_id,
        permission=("create", "TS"),
    )
    named = data.model_dump(exclude_unset=True)
    forced = external_create_values(current_user, "TS", named)
    await check_create_status_right(db, current_user, data.project_id, "TS", named)

    suite_id = await next_doc_id(
        db, TestSuite, TestSuite.suite_id, data.project_id, project.prefix, "TS"
    )
    tag_ids = await creation_tags(db, current_user, data.project_id, data.tag_ids)
    suite = TestSuite(
        project_id=data.project_id,
        created_by_id=current_user.id,
        suite_id=suite_id,
        name=data.name,
        description=data.description,
        status=forced.get("status", data.status),
        visibility=forced.get("visibility", data.visibility),
    )
    db.add(suite)
    await db.flush()
    await attach_tags(db, "test-suite", suite, tag_ids, current_user)
    await db.refresh(suite)

    if data.test_case_ids and await doc_type_visible(db, current_user, data.project_id, "TC"):
        valid_test_case_ids = set(
            (
                await db.execute(
                    apply_external_visibility_filter(
                        select(TestCase.id).where(
                            TestCase.id.in_(data.test_case_ids),
                            TestCase.project_id == data.project_id,
                        ),
                        TestCase,
                        current_user,
                    )
                )
            )
            .scalars()
            .all()
        )
        for index, test_case_id in enumerate(data.test_case_ids):
            if test_case_id in valid_test_case_ids:
                db.add(TestSuiteItem(suite_id=suite.id, test_case_id=test_case_id, order=index))

    await db.flush()
    return await _build_suite_detail(suite, db, current_user)


@router.get("/{suite_id}", response_model=TestSuiteDetailResponse)
async def get_suite(
    suite_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    suite = await get_visible_row(
        db, TestSuite, suite_id, "Test suite not found", current_user, permission=("view", "TS")
    )
    return await _build_suite_detail(suite, db, current_user)


@router.patch("/{suite_id}", response_model=TestSuiteDetailResponse)
async def update_suite(
    suite_id: int,
    data: TestSuiteUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    suite = await get_visible_row(
        db, TestSuite, suite_id, "Test suite not found", current_user, permission=("edit", "TS")
    )
    changes = data.model_dump(exclude_unset=True)
    check_external_change(current_user, "TS", suite, changes)
    await check_status_right(db, current_user, "TS", suite, changes)
    await check_visibility_right(db, current_user, "TS", suite, changes)
    await prepare_workflow_update(db, suite, data, current_user)

    await apply_update(db, suite, data, "test-suite")
    return await _build_suite_detail(suite, db, current_user)


@router.delete("/{suite_id}", status_code=204)
async def delete_suite(
    suite_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    await delete_project_row(
        db,
        current_user,
        TestSuite,
        suite_id,
        "Test suite not found",
        resource="TS",
        audit_type="test-suite",
    )


@router.post("/{suite_id}/items", response_model=TestSuiteItemResponse, status_code=201)
async def add_suite_item(
    suite_id: int,
    test_case_id: int = Query(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    suite = await get_visible_row(
        db, TestSuite, suite_id, "Test suite not found", current_user, permission=("plan", "TS")
    )
    tc = await get_visible_row(
        db,
        TestCase,
        test_case_id,
        "Test case not found in suite project",
        current_user,
        permission=("view", "TC"),
    )
    if tc.project_id != suite.project_id:
        raise HTTPException(status_code=404, detail="Test case not found in suite project")
    existing = (
        await db.execute(
            select(TestSuiteItem).where(
                TestSuiteItem.suite_id == suite_id,
                TestSuiteItem.test_case_id == test_case_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Test case already in suite")

    current_count = (
        await db.execute(
            select(func.count(TestSuiteItem.id)).where(TestSuiteItem.suite_id == suite_id)
        )
    ).scalar() or 0
    await prepare_content_write(db, suite, current_user)
    item = TestSuiteItem(suite_id=suite_id, test_case_id=test_case_id, order=current_count)
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return TestSuiteItemResponse(
        id=item.id,
        suite_id=item.suite_id,
        test_case_id=item.test_case_id,
        order=item.order,
        created_at=item.created_at,
        test_case=test_case_summary(tc),
    )


@router.delete("/{suite_id}/items/{item_id}", status_code=204)
async def remove_suite_item(
    suite_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    suite = await get_visible_row(
        db, TestSuite, suite_id, "Test suite not found", current_user, permission=("plan", "TS")
    )
    item = await get_row_or_404(
        db, TestSuiteItem, item_id, "Suite item not found", TestSuiteItem.suite_id == suite_id
    )
    await prepare_content_write(db, suite, current_user)
    await db.delete(item)
