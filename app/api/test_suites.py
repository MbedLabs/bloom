"""Reusable test suite API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import get_requirement_ids_verified_by_test_cases
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import (
    apply_external_visibility_filter,
    get_current_user,
    require_project_access,
    require_role,
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
from app.models.user import User, UserRole
from app.schemas import (
    PaginatedResponse,
    RequirementSummary,
    TestCampaignSummary,
    TestCaseSummary,
    TestConceptSummary,
    TestSuiteCreate,
    TestSuiteDetailResponse,
    TestSuiteItemResponse,
    TestSuiteResponse,
    TestSuiteUpdate,
)

router = APIRouter()


def _test_case_summary(tc: TestCase) -> TestCaseSummary:
    return TestCaseSummary(id=tc.id, tc_id=tc.tc_id, title=tc.title, status=tc.status)


def _requirement_summary(req: Requirement) -> RequirementSummary:
    return RequirementSummary(id=req.id, req_id=req.req_id, title=req.title, status=req.status)


async def _build_suite_response(suite: TestSuite, db: AsyncSession) -> TestSuiteResponse:
    total_items = (
        await db.execute(
            select(func.count(TestSuiteItem.id)).where(TestSuiteItem.suite_id == suite.id)
        )
    ).scalar() or 0
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
    )


async def _build_suite_detail(
    suite: TestSuite, db: AsyncSession, current_user: User | None = None
) -> TestSuiteDetailResponse:
    base = await _build_suite_response(suite, db)
    items_query = (
        select(TestSuiteItem, TestCase)
        .join(TestCase, TestCase.id == TestSuiteItem.test_case_id)
        .where(TestSuiteItem.suite_id == suite.id)
        .order_by(TestSuiteItem.order, TestSuiteItem.created_at)
    )
    if current_user is not None:
        items_query = apply_external_visibility_filter(items_query, TestCase, current_user)
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
                test_case=_test_case_summary(tc),
            )
        )
        tc_ids.append(tc.id)

    requirement_ids: set[int] = set()
    if tc_ids:
        requirement_ids.update(await get_requirement_ids_verified_by_test_cases(tc_ids, db))

    requirements = []
    if requirement_ids:
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
        requirements = [_requirement_summary(req) for req in reqs]

    campaigns = (
        (
            await db.execute(
                apply_external_visibility_filter(
                    select(TestCampaign)
                    .join(CampaignSuite, CampaignSuite.campaign_id == TestCampaign.id)
                    .where(CampaignSuite.suite_id == suite.id)
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

    # Related concepts: find CPTs linked to any TC in this suite via ArtefactLink
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_project_access(db, current_user, project_id)

    base = select(TestSuite).where(TestSuite.project_id == project_id)
    base = apply_external_visibility_filter(base, TestSuite, current_user)
    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    query = base.order_by(TestSuite.created_at.desc()).offset(skip).limit(limit)
    suites = (await db.execute(query)).scalars().all()

    return PaginatedResponse(
        items=[await _build_suite_response(item, db) for item in suites],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=TestSuiteDetailResponse, status_code=201)
async def create_suite(
    data: TestSuiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    project = (
        await db.execute(select(Project).where(Project.id == data.project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await require_project_access(
        db,
        current_user,
        data.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    suite_id = await next_doc_id(
        db, TestSuite, TestSuite.suite_id, data.project_id, project.prefix, "TS"
    )
    suite = TestSuite(
        project_id=data.project_id,
        suite_id=suite_id,
        name=data.name,
        description=data.description,
        status=data.status,
        visibility=data.visibility,
    )
    db.add(suite)
    await db.flush()
    await db.refresh(suite)

    for index, test_case_id in enumerate(data.test_case_ids):
        tc = (
            await db.execute(select(TestCase).where(TestCase.id == test_case_id))
        ).scalar_one_or_none()
        if tc and tc.project_id == data.project_id:
            db.add(TestSuiteItem(suite_id=suite.id, test_case_id=test_case_id, order=index))

    await db.flush()
    return await _build_suite_detail(suite, db, current_user)


@router.get("/{suite_id}", response_model=TestSuiteDetailResponse)
async def get_suite(
    suite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suite = (
        await db.execute(
            apply_external_visibility_filter(
                select(TestSuite).where(TestSuite.id == suite_id),
                TestSuite,
                current_user,
            )
        )
    ).scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    await require_project_access(db, current_user, suite.project_id)
    return await _build_suite_detail(suite, db, current_user)


@router.patch("/{suite_id}", response_model=TestSuiteDetailResponse)
async def update_suite(
    suite_id: int,
    data: TestSuiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    suite = (
        await db.execute(select(TestSuite).where(TestSuite.id == suite_id))
    ).scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")

    await require_project_access(
        db,
        current_user,
        suite.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(suite, field, value)

    await db.flush()
    await db.refresh(suite)
    return await _build_suite_detail(suite, db, current_user)


@router.delete("/{suite_id}", status_code=204)
async def delete_suite(
    suite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    suite = (
        await db.execute(select(TestSuite).where(TestSuite.id == suite_id))
    ).scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    await require_project_access(
        db,
        current_user,
        suite.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )
    await db.delete(suite)


@router.post("/{suite_id}/items", response_model=TestSuiteItemResponse, status_code=201)
async def add_suite_item(
    suite_id: int,
    test_case_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    suite = (
        await db.execute(select(TestSuite).where(TestSuite.id == suite_id))
    ).scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    await require_project_access(
        db,
        current_user,
        suite.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )
    tc = (
        await db.execute(select(TestCase).where(TestCase.id == test_case_id))
    ).scalar_one_or_none()
    if not tc or tc.project_id != suite.project_id:
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
        test_case=_test_case_summary(tc),
    )


@router.delete("/{suite_id}/items/{item_id}", status_code=204)
async def remove_suite_item(
    suite_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    suite = (
        await db.execute(select(TestSuite).where(TestSuite.id == suite_id))
    ).scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    await require_project_access(
        db,
        current_user,
        suite.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )
    item = (
        await db.execute(
            select(TestSuiteItem).where(
                TestSuiteItem.id == item_id, TestSuiteItem.suite_id == suite_id
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Suite item not found")
    await db.delete(item)
