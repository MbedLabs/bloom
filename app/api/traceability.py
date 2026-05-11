"""
Traceability API endpoints: matrix, impact analysis, coverage gaps.
Cross-requirement relationships use POST /api/links (ArtefactLink).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import (
    get_verifying_test_case_links_for_requirement,
    iter_req_req_incoming_neighbors,
    iter_req_req_outgoing_neighbors,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Requirement, TestCase, TestRunLink
from app.models.user import User
from app.schemas import (
    CoverageGap,
    CoverageGapReport,
    ImpactAnalysisResponse,
    ImpactNode,
    RequirementResponse,
    TestCaseResponse,
    TestRunLinkResponse,
    TraceabilityItem,
)

router = APIRouter()


async def _build_req_response(req: Requirement, db: AsyncSession) -> RequirementResponse:
    tc_count = len(await get_verifying_test_case_links_for_requirement(req.id, db))

    children_result = await db.execute(select(Requirement).where(Requirement.parent_id == req.id))
    children = children_result.scalars().all()

    children_responses = []
    for child in children:
        children_responses.append(await _build_req_response(child, db))

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
        created_at=req.created_at,
        updated_at=req.updated_at,
        children=children_responses,
        test_case_count=tc_count,
    )


async def _build_tc_response(tc: TestCase) -> TestCaseResponse:
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
        requirement_count=0,
    )


async def _get_linked_test_cases(req_id: int, db: AsyncSession):
    linked = []
    for _link, tc in await get_verifying_test_case_links_for_requirement(req_id, db):
        linked.append(await _build_tc_response(tc))
    return linked


async def _get_linked_test_runs(req_id: int, db: AsyncSession):
    tr_links_result = await db.execute(
        select(TestRunLink).where(TestRunLink.requirement_id == req_id)
    )
    tr_links = tr_links_result.scalars().all()
    return [
        TestRunLinkResponse(
            id=tr.id,
            requirement_id=tr.requirement_id,
            test_run_id=tr.test_run_id,
            test_run_name=tr.test_run_name,
            teststation_url=tr.teststation_url,
            status=tr.status,
            created_at=tr.created_at,
        )
        for tr in tr_links
    ]


def _compute_coverage(linked_test_cases: list) -> str:
    tc_count = len(linked_test_cases)
    if tc_count == 0:
        return "Uncovered"
    if all(tc.status == "Draft" for tc in linked_test_cases):
        return "Partial"
    return "Covered"


@router.get("", response_model=list[TraceabilityItem])
async def get_traceability_matrix(
    project_id: int = Query(..., description="Project ID"),
    coverage_filter: Optional[str] = Query(None, description="Filter: Covered, Partial, Uncovered"),
    priority_filter: Optional[str] = Query(None, description="Filter by priority"),
    sort_by: Optional[str] = Query("req_id", description="Sort: req_id, priority, coverage"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Requirement).where(Requirement.project_id == project_id))
    requirements = result.scalars().all()

    items = []
    for req in requirements:
        linked_tcs = await _get_linked_test_cases(req.id, db)
        linked_trs = await _get_linked_test_runs(req.id, db)
        coverage_status = _compute_coverage(linked_tcs)
        req_resp = await _build_req_response(req, db)

        items.append(
            TraceabilityItem(
                requirement=req_resp,
                linked_test_cases=linked_tcs,
                linked_test_runs=linked_trs,
                coverage_status=coverage_status,
            )
        )

    if coverage_filter:
        items = [i for i in items if i.coverage_status == coverage_filter]
    if priority_filter:
        items = [i for i in items if i.requirement.priority == priority_filter]

    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    coverage_order = {"Uncovered": 0, "Partial": 1, "Covered": 2}

    if sort_by == "priority":
        items.sort(key=lambda i: priority_order.get(i.requirement.priority, 99))
    elif sort_by == "coverage":
        items.sort(key=lambda i: coverage_order.get(i.coverage_status, 99))
    else:
        items.sort(key=lambda i: i.requirement.req_id)

    return items


@router.get("/impact/{requirement_id}", response_model=ImpactAnalysisResponse)
async def get_impact_analysis(
    requirement_id: int,
    depth: int = Query(5, description="Max traversal depth"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Requirement).where(Requirement.id == requirement_id))
    root = result.scalar_one_or_none()
    if not root:
        raise HTTPException(status_code=404, detail="Requirement not found")

    root_resp = await _build_req_response(root, db)
    project_id = root.project_id

    async def _build_upstream(req_id: int, current_depth: int, visited: set) -> list:
        if current_depth > depth or req_id in visited:
            return []
        visited.add(req_id)

        nodes = []
        async for src_id, role in iter_req_req_incoming_neighbors(req_id, project_id, db):
            src_result = await db.execute(select(Requirement).where(Requirement.id == src_id))
            src = src_result.scalar_one_or_none()
            if src and src.id not in visited:
                src_resp = await _build_req_response(src, db)
                children = await _build_upstream(src.id, current_depth + 1, visited.copy())
                nodes.append(
                    ImpactNode(
                        requirement=src_resp,
                        link_type=role,
                        direction="upstream",
                        depth=current_depth,
                        children=children,
                    )
                )
        return nodes

    async def _build_downstream(req_id: int, current_depth: int, visited: set) -> list:
        if current_depth > depth or req_id in visited:
            return []
        visited.add(req_id)

        nodes = []
        async for tgt_id, role in iter_req_req_outgoing_neighbors(req_id, project_id, db):
            tgt_result = await db.execute(select(Requirement).where(Requirement.id == tgt_id))
            tgt = tgt_result.scalar_one_or_none()
            if tgt and tgt.id not in visited:
                tgt_resp = await _build_req_response(tgt, db)
                children = await _build_downstream(tgt.id, current_depth + 1, visited.copy())
                nodes.append(
                    ImpactNode(
                        requirement=tgt_resp,
                        link_type=role,
                        direction="downstream",
                        depth=current_depth,
                        children=children,
                    )
                )

        for tc_link, tc in await get_verifying_test_case_links_for_requirement(req_id, db):
            tc_resp = await _build_tc_response(tc)
            nodes.append(
                ImpactNode(
                    requirement=RequirementResponse(
                        id=tc.id,
                        project_id=tc.project_id,
                        parent_id=None,
                        req_id=tc.tc_id,
                        title=tc.title,
                        description=tc.description,
                        status=tc.status,
                        priority="N/A",
                        req_type="test_case",
                        req_origin="N/A",
                        created_at=tc.created_at,
                        updated_at=tc.updated_at,
                        children=[],
                        test_case_count=0,
                    ),
                    link_type=tc_link.role,
                    direction="downstream",
                    depth=current_depth,
                    children=[],
                )
            )
        return nodes

    upstream = await _build_upstream(requirement_id, 1, set())
    downstream = await _build_downstream(requirement_id, 1, set())

    return ImpactAnalysisResponse(
        root_requirement=root_resp,
        upstream=upstream,
        downstream=downstream,
    )


@router.get("/coverage-gaps/{project_id}", response_model=CoverageGapReport)
async def get_coverage_gaps(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Requirement).where(Requirement.project_id == project_id))
    requirements = result.scalars().all()

    gaps = []
    covered = 0
    partial = 0
    uncovered = 0
    for req in requirements:
        linked_tcs = await _get_linked_test_cases(req.id, db)

        tc_count = len(linked_tcs)
        all_draft = tc_count > 0 and all(tc.status == "Draft" for tc in linked_tcs)

        missing: list[str] = []

        if tc_count == 0:
            gap_type = "no_test_cases"
            uncovered += 1
        elif all_draft:
            gap_type = "all_draft"
            partial += 1
        elif missing:
            gap_type = "missing_link_types"
            covered += 1
        else:
            gap_type = "none"
            covered += 1

        if gap_type != "none":
            req_resp = await _build_req_response(req, db)
            gaps.append(
                CoverageGap(
                    requirement=req_resp,
                    gap_type=gap_type,
                    linked_test_cases=linked_tcs,
                    all_test_cases_draft=all_draft,
                    missing_link_types=missing,
                )
            )

    total = len(requirements)
    coverage_pct = round((covered / total * 100) if total > 0 else 0, 1)

    return CoverageGapReport(
        project_id=project_id,
        total_requirements=total,
        covered=covered,
        partial=partial,
        uncovered=uncovered,
        coverage_percent=coverage_pct,
        gaps=gaps,
    )
