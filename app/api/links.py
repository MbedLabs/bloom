"""Generic typed artefact link endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.document_kinds import CANONICAL_DOCUMENT_KINDS
from app.core.link_rules import (
    get_allowed_link_roles,
    get_linkable_type_storage_values,
    is_allowed_link_role,
    is_known_linkable_type,
    normalize_linkable_type,
)
from app.core.security import (
    external_doc_type_allowed,
    get_current_user,
    get_external_doc_types,
    require_project_access,
    require_role,
)
from app.models import (
    ArtefactLink,
    ArtefactVisibility,
    ChangeRequest,
    Defect,
    DesignItem,
    Document,
    Project,
    Requirement,
    RiskItem,
    TestCampaign,
    TestCase,
    TestConcept,
    TestSuite,
)
from app.models.user import User, UserRole
from app.schemas import ArtefactLinkCreate, ArtefactLinkResponse

router = APIRouter()

ARTEFACT_MODELS = {
    "REQ": Requirement,
    "TC": TestCase,
    "DES": DesignItem,
    "RSK": RiskItem,
    "CHG": ChangeRequest,
    "CPT": TestConcept,
    "DEF": Defect,
    "CMP": TestCampaign,
    "TS": TestSuite,
}


def _link_response(row: ArtefactLink) -> ArtefactLinkResponse:
    response = ArtefactLinkResponse.model_validate(row)
    return response.model_copy(
        update={
            "source_type": normalize_linkable_type(response.source_type),
            "target_type": normalize_linkable_type(response.target_type),
        }
    )


async def _artefact_exists_in_project(
    db: AsyncSession, project_id: int, artefact_type: str, artefact_id: int
) -> bool:
    normalized_type = normalize_linkable_type(artefact_type)

    if normalized_type in ARTEFACT_MODELS:
        model = ARTEFACT_MODELS[normalized_type]
        row = (
            await db.execute(
                select(model.id).where(model.project_id == project_id, model.id == artefact_id)
            )
        ).scalar_one_or_none()
        return row is not None

    if normalized_type in CANONICAL_DOCUMENT_KINDS:
        row = (
            await db.execute(
                select(Document.id).where(
                    Document.project_id == project_id,
                    Document.id == artefact_id,
                    Document.doc_type == normalized_type,
                )
            )
        ).scalar_one_or_none()
        return row is not None

    return False


async def _link_endpoint_visible_to_current_user(
    db: AsyncSession,
    project_id: int,
    artefact_type: str,
    artefact_id: int,
    current_user: User,
    allowed_doc_types: set[str] | None,
) -> bool:
    normalized_type = normalize_linkable_type(artefact_type)

    if normalized_type in ARTEFACT_MODELS:
        model = ARTEFACT_MODELS[normalized_type]
        row = (
            await db.execute(
                select(model).where(model.project_id == project_id, model.id == artefact_id)
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        if current_user.role == UserRole.external:
            return getattr(row, "visibility", None) == ArtefactVisibility.customer.value
        return True

    if normalized_type in CANONICAL_DOCUMENT_KINDS:
        row = (
            await db.execute(
                select(Document).where(
                    Document.project_id == project_id,
                    Document.id == artefact_id,
                    Document.doc_type == normalized_type,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        if current_user.role == UserRole.external:
            return (
                row.visibility == ArtefactVisibility.customer.value
                and external_doc_type_allowed(
                    current_user,
                    allowed_doc_types,
                    normalized_type,
                )
            )
        return True

    return False


@router.get("", response_model=list[ArtefactLinkResponse])
async def list_links(
    project_id: int = Query(...),
    source_type: str | None = Query(None),
    source_id: int | None = Query(None),
    target_type: str | None = Query(None),
    target_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_project_access(db, current_user, project_id)
    allowed_doc_types = await get_external_doc_types(db, current_user, project_id)

    query = select(ArtefactLink).where(ArtefactLink.project_id == project_id)
    if source_type:
        query = query.where(
            ArtefactLink.source_type.in_(get_linkable_type_storage_values(source_type))
        )
    if source_id is not None:
        query = query.where(ArtefactLink.source_id == source_id)
    if target_type:
        query = query.where(
            ArtefactLink.target_type.in_(get_linkable_type_storage_values(target_type))
        )
    if target_id is not None:
        query = query.where(ArtefactLink.target_id == target_id)
    rows = (await db.execute(query.order_by(ArtefactLink.created_at.desc()))).scalars().all()

    if current_user.role == UserRole.external:
        visible_rows = []
        for row in rows:
            source_visible = await _link_endpoint_visible_to_current_user(
                db,
                project_id,
                row.source_type,
                row.source_id,
                current_user,
                allowed_doc_types,
            )
            if not source_visible:
                continue

            target_visible = await _link_endpoint_visible_to_current_user(
                db,
                project_id,
                row.target_type,
                row.target_id,
                current_user,
                allowed_doc_types,
            )
            if not target_visible:
                continue

            visible_rows.append(row)
        rows = visible_rows

    return [_link_response(row) for row in rows]


@router.post("", response_model=ArtefactLinkResponse, status_code=201)
async def create_link(
    data: ArtefactLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    data.source_type = normalize_linkable_type(data.source_type)
    data.target_type = normalize_linkable_type(data.target_type)

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
    if not is_known_linkable_type(data.source_type) or not is_known_linkable_type(data.target_type):
        raise HTTPException(status_code=422, detail="Unsupported relationship document kind")
    if data.source_type == data.target_type and data.source_id == data.target_id:
        raise HTTPException(status_code=400, detail="A document cannot link to itself")
    if not is_allowed_link_role(data.source_type, data.target_type, data.role):
        allowed_roles = get_allowed_link_roles(data.source_type, data.target_type)
        if not allowed_roles:
            raise HTTPException(
                status_code=422,
                detail=f"Relationships from {data.source_type} to {data.target_type} are not allowed",
            )
        raise HTTPException(
            status_code=422,
            detail=(
                f"Role '{data.role}' is not allowed for "
                f"{data.source_type} -> {data.target_type}. Allowed roles: {', '.join(allowed_roles)}"
            ),
        )
    source_exists = await _artefact_exists_in_project(
        db, data.project_id, data.source_type, data.source_id
    )
    if not source_exists:
        raise HTTPException(status_code=404, detail="Source document not found in project")
    target_exists = await _artefact_exists_in_project(
        db, data.project_id, data.target_type, data.target_id
    )
    if not target_exists:
        raise HTTPException(status_code=404, detail="Target document not found in project")
    existing = (
        await db.execute(
            select(ArtefactLink).where(
                ArtefactLink.project_id == data.project_id,
                ArtefactLink.source_type.in_(get_linkable_type_storage_values(data.source_type)),
                ArtefactLink.source_id == data.source_id,
                ArtefactLink.target_type.in_(get_linkable_type_storage_values(data.target_type)),
                ArtefactLink.target_id == data.target_id,
                ArtefactLink.role == data.role,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Link already exists")

    link = ArtefactLink(**data.model_dump())
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return _link_response(link)


@router.delete("/{link_id}", status_code=204)
async def delete_link(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    link = (
        await db.execute(select(ArtefactLink).where(ArtefactLink.id == link_id))
    ).scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await require_project_access(
        db,
        current_user,
        link.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )
    await db.delete(link)
