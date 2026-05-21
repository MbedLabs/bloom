"""
Dashboard statistics API.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import dashboard_stats_cache
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import (
    ArtefactLink,
    Defect,
    Project,
    Requirement,
    TestCampaign,
    TestCampaignItem,
    TestCase,
)

OPEN_DEFECT_STATUSES = ("Open", "Triaged", "In Progress", "Resolved", "Verified")
from app.models.user import User

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    cached = dashboard_stats_cache.get("dashboard:stats")
    if cached is not None:
        return cached

    total_projects = await db.scalar(select(func.count(Project.id)))
    active_projects = await db.scalar(
        select(func.count(Project.id)).where(Project.status == "Active")
    )
    total_requirements = await db.scalar(select(func.count(Requirement.id)))
    total_test_cases = await db.scalar(select(func.count(TestCase.id)))

    req_status_result = await db.execute(
        select(Requirement.status, func.count(Requirement.id)).group_by(Requirement.status)
    )
    req_status_dist = {row[0]: row[1] for row in req_status_result}

    tc_status_result = await db.execute(
        select(TestCase.status, func.count(TestCase.id)).group_by(TestCase.status)
    )
    tc_status_dist = {row[0]: row[1] for row in tc_status_result}

    covered_reqs = await db.scalar(
        select(func.count(func.distinct(ArtefactLink.target_id))).where(
            ArtefactLink.source_type == "TC",
            ArtefactLink.target_type == "REQ",
            ArtefactLink.role == "verifies",
        )
    )
    coverage_pct = round((covered_reqs / total_requirements * 100) if total_requirements else 0, 1)

    uncovered_reqs = await db.scalar(
        select(func.count(Requirement.id)).where(
            ~Requirement.id.in_(
                select(ArtefactLink.target_id)
                .where(
                    ArtefactLink.source_type == "TC",
                    ArtefactLink.target_type == "REQ",
                    ArtefactLink.role == "verifies",
                )
                .distinct()
            )
        )
    )

    total_campaigns = await db.scalar(select(func.count(TestCampaign.id)))
    active_campaigns = await db.scalar(
        select(func.count(TestCampaign.id)).where(TestCampaign.status == "In Progress")
    )

    campaign_item_result = await db.execute(
        select(TestCampaignItem.result, func.count(TestCampaignItem.id))
        .where(TestCampaignItem.result.isnot(None))
        .group_by(TestCampaignItem.result)
    )
    campaign_result_dist = {row[0]: row[1] for row in campaign_item_result}

    total_defects = await db.scalar(select(func.count(Defect.id)))
    open_defects = await db.scalar(
        select(func.count(Defect.id)).where(Defect.status.in_(OPEN_DEFECT_STATUSES))
    )
    defect_severity_result = await db.execute(
        select(Defect.severity, func.count(Defect.id))
        .where(Defect.status.in_(OPEN_DEFECT_STATUSES))
        .group_by(Defect.severity)
    )
    defect_severity_dist = {row[0]: row[1] for row in defect_severity_result}
    defect_status_result = await db.execute(
        select(Defect.status, func.count(Defect.id)).group_by(Defect.status)
    )
    defect_status_dist = {row[0]: row[1] for row in defect_status_result}

    project_stats_result = await db.execute(
        select(
            Project.id,
            Project.name,
            Project.prefix,
            Project.status,
            func.count(func.distinct(Requirement.id)).label("req_count"),
            func.count(func.distinct(TestCase.id)).label("tc_count"),
        )
        .outerjoin(Requirement, Requirement.project_id == Project.id)
        .outerjoin(TestCase, TestCase.project_id == Project.id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    )
    project_rows = project_stats_result.all()

    covered_req_ids = (
        select(ArtefactLink.target_id)
        .where(
            ArtefactLink.source_type == "TC",
            ArtefactLink.target_type == "REQ",
            ArtefactLink.role == "verifies",
        )
        .distinct()
    )
    uncovered_by_project_result = await db.execute(
        select(Requirement.project_id, func.count(Requirement.id))
        .where(~Requirement.id.in_(covered_req_ids))
        .group_by(Requirement.project_id)
    )
    uncovered_by_project = {row[0]: row[1] for row in uncovered_by_project_result}

    projects = [
        {
            "id": r.id,
            "name": r.name,
            "prefix": r.prefix,
            "status": r.status,
            "requirement_count": r.req_count,
            "test_case_count": r.tc_count,
            "uncovered_requirement_count": uncovered_by_project.get(r.id, 0),
        }
        for r in project_rows
    ]

    payload = {
        "total_projects": total_projects or 0,
        "active_projects": active_projects or 0,
        "total_requirements": total_requirements or 0,
        "total_test_cases": total_test_cases or 0,
        "total_campaigns": total_campaigns or 0,
        "active_campaigns": active_campaigns or 0,
        "coverage_percent": coverage_pct,
        "uncovered_requirements": uncovered_reqs or 0,
        "requirement_status_distribution": req_status_dist,
        "test_case_status_distribution": tc_status_dist,
        "campaign_result_distribution": campaign_result_dist,
        "total_defects": total_defects or 0,
        "open_defects": open_defects or 0,
        "defect_severity_distribution": defect_severity_dist,
        "defect_status_distribution": defect_status_dist,
        "projects": projects,
    }
    dashboard_stats_cache.set("dashboard:stats", payload)
    return payload
