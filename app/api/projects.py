"""
Projects API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models import Project, Requirement, TestCase, DesignItem, RiskItem, ChangeRequest, TestConcept, TestSuite
from app.models.user import User, UserRole
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter()


async def _project_counts(db: AsyncSession, project_id: int) -> dict[str, int]:
    req_count = (await db.execute(select(func.count(Requirement.id)).where(Requirement.project_id == project_id))).scalar()
    tc_count = (await db.execute(select(func.count(TestCase.id)).where(TestCase.project_id == project_id))).scalar()
    design_count = (await db.execute(select(func.count(DesignItem.id)).where(DesignItem.project_id == project_id))).scalar()
    risk_count = (await db.execute(select(func.count(RiskItem.id)).where(RiskItem.project_id == project_id))).scalar()
    change_count = (await db.execute(select(func.count(ChangeRequest.id)).where(ChangeRequest.project_id == project_id))).scalar()
    test_concept_count = (await db.execute(select(func.count(TestConcept.id)).where(TestConcept.project_id == project_id))).scalar()
    test_suite_count = (await db.execute(select(func.count(TestSuite.id)).where(TestSuite.project_id == project_id))).scalar()

    return {
        "requirement_count": req_count,
        "test_case_count": tc_count,
        "design_count": design_count,
        "risk_count": risk_count,
        "change_count": change_count,
        "test_concept_count": test_concept_count,
        "test_suite_count": test_suite_count,
    }


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    List all projects with requirement and test case counts.
    """
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    response = []
    for project in projects:
        counts = await _project_counts(db, project.id)

        response.append(ProjectResponse(
            id=project.id,
            name=project.name,
            prefix=project.prefix,
            description=project.description,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
            **counts,
        ))

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
    existing = await db.execute(
        select(Project).where(Project.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Project with this name already exists")

    existing_prefix = await db.execute(
        select(Project).where(Project.prefix == data.prefix)
    )
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
        design_count=0,
        risk_count=0,
        change_count=0,
        test_concept_count=0,
        test_suite_count=0,
    )


@router.get("/by-prefix/{prefix}", response_model=ProjectResponse)
async def get_project_by_prefix(
    prefix: str,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    Get a project by its unique prefix.
    """
    result = await db.execute(
        select(Project).where(Project.prefix == prefix.upper())
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    counts = await _project_counts(db, project.id)

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
    _current_user: User = Depends(get_current_user),
):
    """
    Get a project by ID.
    """
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    counts = await _project_counts(db, project.id)

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
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """
    Update a project.
    """
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
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

    counts = await _project_counts(db, project.id)

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
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
