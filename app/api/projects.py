"""
Projects API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import Project, Requirement, TestCase
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
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
        req_count_result = await db.execute(
            select(func.count(Requirement.id)).where(Requirement.project_id == project.id)
        )
        req_count = req_count_result.scalar()

        tc_count_result = await db.execute(
            select(func.count(TestCase.id)).where(TestCase.project_id == project.id)
        )
        tc_count = tc_count_result.scalar()

        response.append(ProjectResponse(
            id=project.id,
            name=project.name,
            prefix=project.prefix,
            description=project.description,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
            requirement_count=req_count,
            test_case_count=tc_count,
        ))

    return response


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
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
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
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

    req_count_result = await db.execute(
        select(func.count(Requirement.id)).where(Requirement.project_id == project.id)
    )
    req_count = req_count_result.scalar()

    tc_count_result = await db.execute(
        select(func.count(TestCase.id)).where(TestCase.project_id == project.id)
    )
    tc_count = tc_count_result.scalar()

    return ProjectResponse(
        id=project.id,
        name=project.name,
        prefix=project.prefix,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        requirement_count=req_count,
        test_case_count=tc_count,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
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

    req_count_result = await db.execute(
        select(func.count(Requirement.id)).where(Requirement.project_id == project.id)
    )
    req_count = req_count_result.scalar()

    tc_count_result = await db.execute(
        select(func.count(TestCase.id)).where(TestCase.project_id == project.id)
    )
    tc_count = tc_count_result.scalar()

    return ProjectResponse(
        id=project.id,
        name=project.name,
        prefix=project.prefix,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        requirement_count=req_count,
        test_case_count=tc_count,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
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
