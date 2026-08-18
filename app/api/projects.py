"""
Projects API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    get_current_user,
    get_external_doc_types,
    require_project_access,
    require_role,
)
from app.models import (
    ArtefactLink,
    Baseline,
    CampaignSuite,
    ChangeRequest,
    Defect,
    DefectSyncEvent,
    DesignItem,
    Document,
    DocumentSection,
    IntegrationSetting,
    Project,
    ProjectVariable,
    Requirement,
    RequirementLink,
    RiskItem,
    TestCampaign,
    TestCampaignItem,
    TestCase,
    TestConcept,
    TestRunLink,
    TestSuite,
    TestSuiteItem,
)
from app.models.project_membership import ProjectMembership
from app.models.user import User, UserRole
from app.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.coverage import coverage_percent as coverage_percent_of
from app.services.coverage import covered_requirement_ids

router = APIRouter()


async def _delete_project_scoped_data(db: AsyncSession, project_id: int) -> None:
    requirement_ids = select(Requirement.id).where(Requirement.project_id == project_id)
    defect_ids = select(Defect.id).where(Defect.project_id == project_id)
    document_ids = select(Document.id).where(Document.project_id == project_id)
    campaign_ids = select(TestCampaign.id).where(TestCampaign.project_id == project_id)
    suite_ids = select(TestSuite.id).where(TestSuite.project_id == project_id)

    await db.execute(delete(DefectSyncEvent).where(DefectSyncEvent.defect_id.in_(defect_ids)))
    await db.execute(delete(TestCampaignItem).where(TestCampaignItem.campaign_id.in_(campaign_ids)))
    await db.execute(delete(CampaignSuite).where(CampaignSuite.campaign_id.in_(campaign_ids)))
    await db.execute(delete(TestSuiteItem).where(TestSuiteItem.suite_id.in_(suite_ids)))
    await db.execute(delete(ArtefactLink).where(ArtefactLink.project_id == project_id))
    await db.execute(
        delete(RequirementLink).where(
            or_(
                RequirementLink.source_id.in_(requirement_ids),
                RequirementLink.target_id.in_(requirement_ids),
            )
        )
    )
    await db.execute(delete(TestRunLink).where(TestRunLink.requirement_id.in_(requirement_ids)))
    await db.execute(delete(DocumentSection).where(DocumentSection.document_id.in_(document_ids)))
    await db.execute(delete(IntegrationSetting).where(IntegrationSetting.project_id == project_id))
    await db.execute(delete(ProjectVariable).where(ProjectVariable.project_id == project_id))
    await db.execute(delete(TestCampaign).where(TestCampaign.project_id == project_id))
    await db.execute(delete(TestSuite).where(TestSuite.project_id == project_id))
    await db.execute(delete(Defect).where(Defect.project_id == project_id))
    await db.execute(delete(TestCase).where(TestCase.project_id == project_id))
    await db.execute(delete(Document).where(Document.project_id == project_id))
    await db.execute(delete(DesignItem).where(DesignItem.project_id == project_id))
    await db.execute(delete(RiskItem).where(RiskItem.project_id == project_id))
    await db.execute(delete(ChangeRequest).where(ChangeRequest.project_id == project_id))
    await db.execute(delete(Baseline).where(Baseline.project_id == project_id))
    await db.execute(delete(TestConcept).where(TestConcept.project_id == project_id))
    await db.execute(
        update(Requirement).where(Requirement.project_id == project_id).values(parent_id=None)
    )
    await db.execute(delete(Requirement).where(Requirement.project_id == project_id))


async def _project_counts(
    db: AsyncSession,
    project_id: int,
    current_user: User,
) -> dict[str, int]:
    external = current_user.role == UserRole.external
    allowed_doc_types = (
        await get_external_doc_types(db, current_user, project_id) if external else None
    )

    async def count_visible(model, doc_type: str) -> int:
        if allowed_doc_types is not None and doc_type not in allowed_doc_types:
            return 0
        query = select(func.count(model.id)).where(model.project_id == project_id)
        if external:
            query = query.where(model.visibility == "customer")
        return (await db.scalar(query)) or 0

    req_count = await count_visible(Requirement, "REQ")
    tc_count = await count_visible(TestCase, "TC")
    campaign_count = await count_visible(TestCampaign, "CMP")
    design_count = await count_visible(DesignItem, "DES")
    risk_count = await count_visible(RiskItem, "RSK")
    change_count = await count_visible(ChangeRequest, "CHG")
    test_concept_count = await count_visible(TestConcept, "CPT")
    test_suite_count = await count_visible(TestSuite, "TS")
    defect_count = await count_visible(Defect, "DEF")

    covered_query = covered_requirement_ids().where(ArtefactLink.project_id == project_id)
    if external:
        if allowed_doc_types is not None and not {"REQ", "TC"}.issubset(allowed_doc_types):
            covered_query = None
        else:
            covered_query = covered_query.where(
                Requirement.visibility == "customer",
                TestCase.visibility == "customer",
            )
    if covered_query is None:
        covered_reqs = 0
    else:
        covered_reqs = (
            await db.scalar(select(func.count()).select_from(covered_query.distinct().subquery()))
        ) or 0
    coverage_percent = coverage_percent_of(covered_reqs, req_count or 0)
    uncovered_requirement_count = max((req_count or 0) - (covered_reqs or 0), 0)

    return {
        "requirement_count": req_count,
        "test_case_count": tc_count,
        "campaign_count": campaign_count,
        "design_count": design_count,
        "risk_count": risk_count,
        "change_count": change_count,
        "test_concept_count": test_concept_count,
        "test_suite_count": test_suite_count,
        "defect_count": defect_count,
        "coverage_percent": coverage_percent,
        "uncovered_requirement_count": uncovered_requirement_count,
    }


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all projects with requirement and test case counts.
    """
    query = select(Project).order_by(Project.created_at.desc())
    if current_user.role != UserRole.admin:
        query = (
            select(Project)
            .join(ProjectMembership, ProjectMembership.project_id == Project.id)
            .where(ProjectMembership.user_id == current_user.id)
            .order_by(Project.created_at.desc())
        )
    result = await db.execute(query)
    projects = result.scalars().all()

    response = []
    for project in projects:
        counts = await _project_counts(db, project.id, current_user)

        response.append(
            ProjectResponse(
                id=project.id,
                name=project.name,
                prefix=project.prefix,
                description=project.description,
                status=project.status,
                created_at=project.created_at,
                updated_at=project.updated_at,
                **counts,
            )
        )

    return response


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Create a new project.
    """
    existing = await db.execute(select(Project).where(Project.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Project with this name already exists")

    existing_prefix = await db.execute(select(Project).where(Project.prefix == data.prefix))
    if existing_prefix.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Project with this prefix already exists")

    project = Project(
        name=data.name,
        prefix=data.prefix,
        description=data.description,
        status=data.status,
    )

    db.add(project)
    await db.flush()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        prefix=project.prefix,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        requirement_count=0,
        test_case_count=0,
        campaign_count=0,
        design_count=0,
        risk_count=0,
        change_count=0,
        test_concept_count=0,
        test_suite_count=0,
        defect_count=0,
    )


@router.get("/by-prefix/{prefix}", response_model=ProjectResponse)
async def get_project_by_prefix(
    prefix: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a project by its unique prefix.
    """
    result = await db.execute(select(Project).where(Project.prefix == prefix.upper()))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await require_project_access(db, current_user, project.id)

    counts = await _project_counts(db, project.id, current_user)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        prefix=project.prefix,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        **counts,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a project by ID.
    """
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await require_project_access(db, current_user, project_id)

    counts = await _project_counts(db, project.id, current_user)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        prefix=project.prefix,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        **counts,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """
    Update a project.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.name is not None:
        existing = await db.execute(
            select(Project).where(Project.name == data.name, Project.id != project_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Project with this name already exists")
        project.name = data.name

    if data.prefix is not None:
        existing_prefix = await db.execute(
            select(Project).where(Project.prefix == data.prefix, Project.id != project_id)
        )
        if existing_prefix.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Project with this prefix already exists")
        project.prefix = data.prefix

    if data.description is not None:
        project.description = data.description
    if data.status is not None:
        project.status = data.status

    await db.flush()
    await db.refresh(project)

    counts = await _project_counts(db, project.id, current_user)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        prefix=project.prefix,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        **counts,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin)),
):
    """
    Delete a project.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await _delete_project_scoped_data(db, project_id)
    await db.delete(project)
