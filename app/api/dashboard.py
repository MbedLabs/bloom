"""
Dashboard statistics API.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import dashboard_stats_cache
from app.core.database import get_db
from app.core.security import apply_external_visibility_filter, get_current_user
from app.models import (
    ArtefactLink,
    Defect,
    Project,
    ProjectMembership,
    Requirement,
    TestCampaign,
    TestCampaignItem,
    TestCase,
)
from app.models.project_membership import ProjectExternalDocType
from app.models.user import User, UserRole

OPEN_DEFECT_STATUSES = ("Open", "Triaged", "In Progress", "Resolved", "Verified")

VALID_DOCUMENT_STATUSES = {
    "Draft",
    "Review",
    "Approved",
    "Active",
    "Final",
    "Implemented",
    "Verified",
    "Rejected",
    "Obsolete",
    "Deprecated",
    "Superseded",
}

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_scope = f"user:{current_user.id}" if current_user.role != UserRole.admin else "admin"
    cache_key = f"dashboard:stats:{user_scope}"
    cached = dashboard_stats_cache.get(cache_key)
    if cached is not None:
        return cached

    accessible_project_ids = None
    allowed_project_ids_by_doc_type: dict[str, set[int]] = {}
    if current_user.role != UserRole.admin:
        membership_result = await db.execute(
            select(ProjectMembership.project_id).where(ProjectMembership.user_id == current_user.id)
        )
        accessible_project_ids = membership_result.scalars().all()
        if not accessible_project_ids:
            payload = {
                "total_projects": 0,
                "active_projects": 0,
                "total_requirements": 0,
                "total_test_cases": 0,
                "total_campaigns": 0,
                "active_campaigns": 0,
                "coverage_percent": 0,
                "uncovered_requirements": 0,
                "requirement_status_distribution": {},
                "test_case_status_distribution": {},
                "campaign_result_distribution": {},
                "total_defects": 0,
                "open_defects": 0,
                "defect_severity_distribution": {},
                "defect_status_distribution": {},
                "projects": [],
            }
            dashboard_stats_cache.set(cache_key, payload)
            return payload
        if current_user.role == UserRole.external:
            allowed_rows = await db.execute(
                select(ProjectMembership.project_id, ProjectExternalDocType.doc_type)
                .join(
                    ProjectExternalDocType,
                    ProjectExternalDocType.membership_id == ProjectMembership.id,
                )
                .where(ProjectMembership.user_id == current_user.id)
            )
            for project_id, doc_type in allowed_rows:
                allowed_project_ids_by_doc_type.setdefault(doc_type, set()).add(project_id)

    def _restrict(query, model, *, project_field: str = "project_id"):
        if accessible_project_ids is None:
            return query
        return query.where(getattr(model, project_field).in_(accessible_project_ids))

    def _restrict_visible(query, model, doc_type: str, *, project_field: str = "project_id"):
        query = _restrict(query, model, project_field=project_field)
        if current_user.role == UserRole.external:
            query = query.where(
                getattr(model, project_field).in_(
                    allowed_project_ids_by_doc_type.get(doc_type, set())
                )
            )
        return apply_external_visibility_filter(query, model, current_user)

    total_projects = await db.scalar(
        _restrict(select(func.count(Project.id)), Project, project_field="id")
    )
    active_projects = await db.scalar(
        _restrict(
            select(func.count(Project.id)).where(Project.status == "Active"),
            Project,
            project_field="id",
        )
    )
    total_requirements = await db.scalar(
        _restrict_visible(select(func.count(Requirement.id)), Requirement, "REQ")
    )
    total_test_cases = await db.scalar(
        _restrict_visible(select(func.count(TestCase.id)), TestCase, "TC")
    )

    req_status_result = await db.execute(
        _restrict_visible(
            select(Requirement.status, func.count(Requirement.id)).group_by(Requirement.status),
            Requirement,
            "REQ",
        )
    )
    req_status_dist = {
        row[0]: row[1] for row in req_status_result if row[0] in VALID_DOCUMENT_STATUSES
    }

    tc_status_result = await db.execute(
        _restrict_visible(
            select(TestCase.status, func.count(TestCase.id)).group_by(TestCase.status),
            TestCase,
            "TC",
        )
    )
    tc_status_dist = {
        row[0]: row[1] for row in tc_status_result if row[0] in VALID_DOCUMENT_STATUSES
    }

    covered_req_ids = (
        select(ArtefactLink.target_id)
        .join(TestCase, TestCase.id == ArtefactLink.source_id)
        .join(Requirement, Requirement.id == ArtefactLink.target_id)
        .where(
            ArtefactLink.source_type == "TC",
            ArtefactLink.target_type == "REQ",
            ArtefactLink.role == "verifies",
        )
    )
    covered_req_ids = _restrict_visible(covered_req_ids, TestCase, "TC").where(
        Requirement.project_id.in_(accessible_project_ids)
        if accessible_project_ids is not None
        else True
    )
    if current_user.role == UserRole.external:
        covered_req_ids = covered_req_ids.where(
            Requirement.project_id.in_(allowed_project_ids_by_doc_type.get("REQ", set()))
        )
    covered_req_ids = apply_external_visibility_filter(covered_req_ids, Requirement, current_user)
    covered_reqs = await db.scalar(
        select(func.count(func.distinct(covered_req_ids.subquery().c.target_id)))
    )
    coverage_pct = round((covered_reqs / total_requirements * 100) if total_requirements else 0, 1)

    uncovered_reqs = await db.scalar(
        _restrict_visible(
            select(func.count(Requirement.id)).where(
                ~Requirement.id.in_(
                    covered_req_ids.with_only_columns(ArtefactLink.target_id).distinct()
                )
            ),
            Requirement,
            "REQ",
        )
    )

    total_campaigns = await db.scalar(
        _restrict_visible(select(func.count(TestCampaign.id)), TestCampaign, "CMP")
    )
    active_campaigns = await db.scalar(
        _restrict_visible(
            select(func.count(TestCampaign.id)).where(TestCampaign.status == "In Progress"),
            TestCampaign,
            "CMP",
        )
    )

    campaign_item_query = (
        select(TestCampaignItem.result, func.count(TestCampaignItem.id))
        .join(TestCampaign, TestCampaign.id == TestCampaignItem.campaign_id)
        .where(TestCampaignItem.result.isnot(None))
        .group_by(TestCampaignItem.result)
    )
    if accessible_project_ids is not None:
        campaign_item_query = campaign_item_query.where(
            TestCampaign.project_id.in_(accessible_project_ids)
        )
    if current_user.role == UserRole.external:
        campaign_item_query = campaign_item_query.where(
            TestCampaign.project_id.in_(allowed_project_ids_by_doc_type.get("CMP", set()))
        )
    campaign_item_query = apply_external_visibility_filter(
        campaign_item_query, TestCampaign, current_user
    )
    campaign_item_result = await db.execute(campaign_item_query)
    campaign_result_dist = {row[0]: row[1] for row in campaign_item_result}

    total_defects = await db.scalar(_restrict_visible(select(func.count(Defect.id)), Defect, "DEF"))
    open_defects = await db.scalar(
        _restrict_visible(
            select(func.count(Defect.id)).where(Defect.status.in_(OPEN_DEFECT_STATUSES)),
            Defect,
            "DEF",
        )
    )
    defect_severity_result = await db.execute(
        _restrict_visible(
            select(Defect.severity, func.count(Defect.id))
            .where(Defect.status.in_(OPEN_DEFECT_STATUSES))
            .group_by(Defect.severity),
            Defect,
            "DEF",
        )
    )
    defect_severity_dist = {row[0]: row[1] for row in defect_severity_result}
    defect_status_result = await db.execute(
        _restrict_visible(
            select(Defect.status, func.count(Defect.id)).group_by(Defect.status),
            Defect,
            "DEF",
        )
    )
    defect_status_dist = {row[0]: row[1] for row in defect_status_result}

    req_count_query = select(func.count(Requirement.id)).where(Requirement.project_id == Project.id)
    tc_count_query = select(func.count(TestCase.id)).where(TestCase.project_id == Project.id)
    if current_user.role == UserRole.external:
        req_count_query = req_count_query.where(
            Project.id.in_(allowed_project_ids_by_doc_type.get("REQ", set())),
            Requirement.visibility == "customer",
        )
        tc_count_query = tc_count_query.where(
            Project.id.in_(allowed_project_ids_by_doc_type.get("TC", set())),
            TestCase.visibility == "customer",
        )
    project_query = select(
        Project.id,
        Project.name,
        Project.prefix,
        Project.status,
        req_count_query.scalar_subquery().label("req_count"),
        tc_count_query.scalar_subquery().label("tc_count"),
    )
    if accessible_project_ids is not None:
        project_query = project_query.where(Project.id.in_(accessible_project_ids))
    project_stats_result = await db.execute(project_query.order_by(Project.created_at.desc()))
    project_rows = project_stats_result.all()

    uncovered_by_project_result = await db.execute(
        _restrict_visible(
            select(Requirement.project_id, func.count(Requirement.id))
            .where(~Requirement.id.in_(covered_req_ids))
            .group_by(Requirement.project_id),
            Requirement,
            "REQ",
        )
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
    dashboard_stats_cache.set(cache_key, payload)
    return payload
