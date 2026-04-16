"""
Dashboard statistics API.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import (
    Document,
    Project,
    Requirement,
    RequirementTestCase,
    TestCampaign,
    TestCampaignItem,
    TestCase,
)
from app.models.user import User

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    total_projects = await db.scalar(select(func.count(Project.id)))
    active_projects = await db.scalar(
        select(func.count(Project.id)).where(Project.status == "Active")
    )
    total_requirements = await db.scalar(select(func.count(Requirement.id)))
    total_test_cases = await db.scalar(select(func.count(TestCase.id)))
    total_documents = await db.scalar(select(func.count(Document.id)))

    req_status_result = await db.execute(
        select(Requirement.status, func.count(Requirement.id)).group_by(Requirement.status)
    )
    req_status_dist = {row[0]: row[1] for row in req_status_result}

    tc_status_result = await db.execute(
        select(TestCase.status, func.count(TestCase.id)).group_by(TestCase.status)
    )
    tc_status_dist = {row[0]: row[1] for row in tc_status_result}

    total_links = await db.scalar(select(func.count(RequirementTestCase.id)))
    coverage_pct = round((total_links / total_requirements * 100) if total_requirements else 0, 1)

    uncovered_reqs = await db.scalar(
        select(func.count(Requirement.id)).where(
            ~Requirement.id.in_(select(RequirementTestCase.requirement_id).distinct())
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
        .limit(10)
    )
    project_rows = project_stats_result.all()
    projects = [
        {
            "id": r.id,
            "name": r.name,
            "prefix": r.prefix,
            "status": r.status,
            "requirement_count": r.req_count,
            "test_case_count": r.tc_count,
        }
        for r in project_rows
    ]

    return {
        "total_projects": total_projects or 0,
        "active_projects": active_projects or 0,
        "total_requirements": total_requirements or 0,
        "total_test_cases": total_test_cases or 0,
        "total_documents": total_documents or 0,
        "total_campaigns": total_campaigns or 0,
        "active_campaigns": active_campaigns or 0,
        "coverage_percent": coverage_pct,
        "uncovered_requirements": uncovered_reqs or 0,
        "requirement_status_distribution": req_status_dist,
        "test_case_status_distribution": tc_status_dist,
        "campaign_result_distribution": campaign_result_dist,
        "projects": projects,
    }
