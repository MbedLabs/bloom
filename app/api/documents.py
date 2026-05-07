"""
Documents API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.document_kinds import normalize_document_kind, require_document_kind
from app.core.id_generator import normalize_doc_id
from app.core.security import get_current_user, require_role
from app.models import Document, DocumentSection
from app.models.user import User, UserRole
from app.schemas import (
    DocumentCreate,
    DocumentDetailResponse,
    DocumentResponse,
    DocumentSectionCreate,
    DocumentSectionResponse,
    DocumentSectionUpdate,
    DocumentUpdate,
    SectionReorder,
)

router = APIRouter()


@router.get("/projects/{project_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    response = []
    for doc in documents:
        section_count_result = await db.execute(
            select(func.count(DocumentSection.id)).where(DocumentSection.document_id == doc.id)
        )
        section_count = section_count_result.scalar()

        response.append(
            DocumentResponse(
                id=doc.id,
                project_id=doc.project_id,
                doc_id=doc.doc_id,
                title=doc.title,
                doc_type=normalize_document_kind(doc.doc_type),
                status=doc.status,
                version=doc.version,
                description=doc.description,
                content_json=doc.content_json,
                content_html=doc.content_html,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                section_count=section_count,
            )
        )

    return response


@router.post("/projects/{project_id}/documents", response_model=DocumentResponse, status_code=201)
async def create_document(
    project_id: int,
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    from app.models import Project

    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    type_code = require_document_kind(data.doc_type)
    try:
        doc_id = normalize_doc_id(
            data.doc_id,
            expected_type_code=type_code,
            expected_project_prefix=project.prefix,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = await db.execute(
        select(Document).where(
            Document.project_id == project_id,
            Document.doc_id == doc_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Document with this ID already exists")
    document = Document(
        project_id=project_id,
        doc_id=doc_id,
        title=data.title,
        doc_type=type_code,
        description=data.description,
        content_json=data.content_json,
        content_html=data.content_html,
    )

    db.add(document)
    await db.flush()
    await db.refresh(document)

    return DocumentResponse(
        id=document.id,
        project_id=document.project_id,
        doc_id=document.doc_id,
        title=document.title,
        doc_type=normalize_document_kind(document.doc_type),
        status=document.status,
        version=document.version,
        description=document.description,
        content_json=document.content_json,
        content_html=document.content_html,
        created_at=document.created_at,
        updated_at=document.updated_at,
        section_count=0,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    sections_result = await db.execute(
        select(DocumentSection)
        .where(
            DocumentSection.document_id == document_id,
            DocumentSection.parent_section_id.is_(None),
        )
        .order_by(DocumentSection.order)
    )
    root_sections = sections_result.scalars().all()

    async def build_section_tree(section):
        children_result = await db.execute(
            select(DocumentSection)
            .where(DocumentSection.parent_section_id == section.id)
            .order_by(DocumentSection.order)
        )
        children = children_result.scalars().all()
        child_responses = []
        for child in children:
            child_resp = await build_section_tree(child)
            child_responses.append(child_resp)
        return DocumentSectionResponse(
            id=section.id,
            document_id=section.document_id,
            parent_section_id=section.parent_section_id,
            order=section.order,
            title=section.title,
            content=section.content,
            section_type=section.section_type,
            created_at=section.created_at,
            updated_at=section.updated_at,
            child_sections=child_responses,
        )

    section_responses = []
    for section in root_sections:
        resp = await build_section_tree(section)
        section_responses.append(resp)

    return DocumentDetailResponse(
        id=document.id,
        project_id=document.project_id,
        doc_id=document.doc_id,
        title=document.title,
        doc_type=normalize_document_kind(document.doc_type),
        status=document.status,
        version=document.version,
        description=document.description,
        content_json=document.content_json,
        content_html=document.content_html,
        created_at=document.created_at,
        updated_at=document.updated_at,
        sections=section_responses,
    )


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if data.title is not None:
        document.title = data.title
    if data.doc_type is not None:
        document.doc_type = require_document_kind(data.doc_type)
    if data.status is not None:
        document.status = data.status
    if data.version is not None:
        document.version = data.version
    if data.description is not None:
        document.description = data.description
    if data.content_json is not None:
        document.content_json = data.content_json
    if data.content_html is not None:
        document.content_html = data.content_html

    await db.flush()
    await db.refresh(document)

    section_count_result = await db.execute(
        select(func.count(DocumentSection.id)).where(DocumentSection.document_id == document.id)
    )
    section_count = section_count_result.scalar()

    return DocumentResponse(
        id=document.id,
        project_id=document.project_id,
        doc_id=document.doc_id,
        title=document.title,
        doc_type=normalize_document_kind(document.doc_type),
        status=document.status,
        version=document.version,
        description=document.description,
        content_json=document.content_json,
        content_html=document.content_html,
        created_at=document.created_at,
        updated_at=document.updated_at,
        section_count=section_count,
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.delete(document)


@router.post(
    "/documents/{document_id}/sections",
    response_model=DocumentSectionResponse,
    status_code=201,
)
async def create_section(
    document_id: int,
    data: DocumentSectionCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    section = DocumentSection(
        document_id=document_id,
        title=data.title,
        content=data.content,
        section_type=data.section_type,
        order=data.order,
        parent_section_id=data.parent_section_id,
    )

    db.add(section)
    await db.flush()
    await db.refresh(section)

    return DocumentSectionResponse(
        id=section.id,
        document_id=section.document_id,
        parent_section_id=section.parent_section_id,
        order=section.order,
        title=section.title,
        content=section.content,
        section_type=section.section_type,
        created_at=section.created_at,
        updated_at=section.updated_at,
        child_sections=[],
    )


@router.patch("/document-sections/{section_id}", response_model=DocumentSectionResponse)
async def update_section(
    section_id: int,
    data: DocumentSectionUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(DocumentSection).where(DocumentSection.id == section_id))
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    if data.title is not None:
        section.title = data.title
    if data.content is not None:
        section.content = data.content
    if data.section_type is not None:
        section.section_type = data.section_type
    if data.order is not None:
        section.order = data.order
    if data.parent_section_id is not None:
        section.parent_section_id = data.parent_section_id
    await db.flush()
    await db.refresh(section)

    children_result = await db.execute(
        select(DocumentSection)
        .where(DocumentSection.parent_section_id == section.id)
        .order_by(DocumentSection.order)
    )
    children = children_result.scalars().all()

    return DocumentSectionResponse(
        id=section.id,
        document_id=section.document_id,
        parent_section_id=section.parent_section_id,
        order=section.order,
        title=section.title,
        content=section.content,
        section_type=section.section_type,
        created_at=section.created_at,
        updated_at=section.updated_at,
        child_sections=[
            DocumentSectionResponse(
                id=c.id,
                document_id=c.document_id,
                parent_section_id=c.parent_section_id,
                order=c.order,
                title=c.title,
                content=c.content,
                section_type=c.section_type,
                created_at=c.created_at,
                updated_at=c.updated_at,
                child_sections=[],
            )
            for c in children
        ],
    )


@router.delete("/document-sections/{section_id}", status_code=204)
async def delete_section(
    section_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(DocumentSection).where(DocumentSection.id == section_id))
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    await db.delete(section)


@router.post("/documents/{document_id}/sections/reorder")
async def reorder_sections(
    document_id: int,
    data: SectionReorder,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    for item in data.section_orders:
        section_result = await db.execute(
            select(DocumentSection).where(
                DocumentSection.id == item["id"],
                DocumentSection.document_id == document_id,
            )
        )
        section = section_result.scalar_one_or_none()
        if section:
            section.order = item["order"]

    await db.flush()

    return {"detail": "Sections reordered successfully"}
