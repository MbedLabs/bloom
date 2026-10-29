"""
Unified docs facade: PLM-style lookup by string doc_id across all type tables,
and a unified list endpoint for all doc types within a project.
"""

from datetime import date, datetime, time
from http import HTTPStatus
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_serializer
from sqlalchemy import (
    DateTime,
    Integer,
    String,
    and_,
    case,
    cast,
    func,
    literal,
    null,
    or_,
    select,
    true,
    union_all,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.artefact_utils import (
    allowed_actions,
    holds,
    mark_refused_if_found,
    type_visible,
    visible_types,
)
from app.core.database import get_db
from app.core.document_kinds import (
    CANONICAL_DOCUMENT_KINDS,
    document_kind_from_slug,
    normalize_document_kind,
)
from app.core.id_generator import next_doc_id
from app.core.security import (
    apply_external_visibility_filter,
    external_doc_type_allowed,
    get_current_user,
    get_external_doc_types,
    require_project_access,
)
from app.models import (
    ArtefactLink,
    ArtefactVisibility,
    CampaignSuite,
    ChangeRequest,
    Defect,
    DesignItem,
    Document,
    Project,
    Requirement,
    RiskItem,
    TestCampaign,
    TestCampaignItem,
    TestCase,
    TestConcept,
    TestSuite,
    TestSuiteItem,
)
from app.models.tags import TAG_TYPE_OF_MODEL
from app.models.user import User
from app.models.workflow import ArtefactWorkflow
from app.schemas import PaginatedResponse
from app.services.audit import mark_refused
from app.services.document_workflow import (
    CONTROLLED_TYPES,
    LEGACY_CHANGE_STATUSES,
    WORKFLOW_PHASES,
    current_status,
)

router = APIRouter()


class DocShellResponse(BaseModel):
    id: int
    doc_id: str
    doc_type: str
    title: str
    status: str | None
    visibility: str = ArtefactVisibility.internal.value
    priority: str | None = None
    req_type: str | None = None
    req_origin: str | None = None
    project_id: int
    reviewer_id: int | None = None
    incoming_links: int = 0
    outgoing_links: int = 0
    suspect_links: int = 0
    last_execution_status: str | None = None
    last_executed_at: datetime | None = None
    last_bud_run_id: int | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("last_executed_at", "created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None


class DocDetailFacadeResponse(DocShellResponse):
    """One artefact with its body, and the changing actions the reader may take on it."""

    description: str | None = None
    content_json: dict | None = None
    content_html: str | None = None
    allowed_actions: list[str] = []

    @field_serializer("last_executed_at", "created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None


async def resolve_project(db: AsyncSession, identifier: str) -> Project:
    """Resolve a project by numeric ID or string prefix."""
    if identifier.isdigit():
        result = await db.execute(select(Project).where(Project.id == int(identifier)))
    else:
        result = await db.execute(select(Project).where(Project.prefix == identifier.upper()))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


TYPE_MAP = {
    "REQ": (Requirement, "req_id", "requirements"),
    "TC": (TestCase, "tc_id", "test-cases"),
    "DES": (DesignItem, "design_id", "designs"),
    "RSK": (RiskItem, "risk_id", "risks"),
    "CHG": (ChangeRequest, "change_id", "changes"),
    "CPT": (TestConcept, "concept_id", "test-concepts"),
    "DEF": (Defect, "defect_id", "defects"),
    "CMP": (TestCampaign, "campaign_id", "campaigns"),
    "TS": (TestSuite, "suite_id", "test-suites"),
}

LEGACY_TYPE_SLUG_ALIASES = {
    "test_cases": "test-cases",
    "design_items": "designs",
    "risk_items": "risks",
    "change_requests": "changes",
    "test_concepts": "test-concepts",
}


def _get_priority(model, row):
    """Extract priority from a model row, handling models without a priority column."""
    if hasattr(model, "priority"):
        return row.priority
    if hasattr(model, "severity"):
        return row.severity
    return None


def _get_reviewer_id(model, row) -> int | None:
    """Extract reviewer_id from a model row, if the column exists."""
    return getattr(row, "reviewer_id", None)


def _resolved_doc_type(type_code: str, row) -> str:
    """Resolve a facade doc_type for generic Document rows."""
    if type_code == "DOCUMENT":
        return normalize_document_kind(getattr(row, "doc_type", None))
    return type_code


async def _count_links(
    db: AsyncSession,
    project_id: int,
    type_code: str,
    row_ids: list[int],
    types: frozenset[str] | None = None,
) -> dict[int, dict]:
    """Return {row_id: {incoming, outgoing, suspect}} for the given rows, counting only
    links whose other end is of a type in ``types`` (None: every type)."""
    if not row_ids:
        return {}
    incoming_q = (
        select(
            ArtefactLink.target_id,
            func.count().label("cnt"),
            func.sum(case((ArtefactLink.suspect.is_(True), 1), else_=0)).label("suspect_cnt"),
        )
        .where(
            ArtefactLink.project_id == project_id,
            ArtefactLink.target_type == type_code,
            ArtefactLink.target_id.in_(row_ids),
            true() if types is None else ArtefactLink.source_type.in_(types),
        )
        .group_by(ArtefactLink.target_id)
    )
    outgoing_q = (
        select(
            ArtefactLink.source_id,
            func.count().label("cnt"),
            func.sum(case((ArtefactLink.suspect.is_(True), 1), else_=0)).label("suspect_cnt"),
        )
        .where(
            ArtefactLink.project_id == project_id,
            ArtefactLink.source_type == type_code,
            ArtefactLink.source_id.in_(row_ids),
            true() if types is None else ArtefactLink.target_type.in_(types),
        )
        .group_by(ArtefactLink.source_id)
    )
    incoming_rows = (await db.execute(incoming_q)).all()
    outgoing_rows = (await db.execute(outgoing_q)).all()
    result: dict[int, dict] = {rid: {"incoming": 0, "outgoing": 0, "suspect": 0} for rid in row_ids}
    for target_id, cnt, suspect_cnt in incoming_rows:
        if target_id in result:
            result[target_id]["incoming"] = cnt
            result[target_id]["suspect"] = suspect_cnt
    for source_id, cnt, suspect_cnt in outgoing_rows:
        if source_id in result:
            result[source_id]["outgoing"] = cnt
            result[source_id]["suspect"] += suspect_cnt or 0
    return result


async def _resolve_doc_by_public_id(
    db: AsyncSession, project_id: int, public_id: str
) -> tuple[str, int] | None:
    """Resolve a document ID such as ``PRJ-REQ-001`` to its type code and row id."""
    for type_code, (model, id_col_name, _slug) in TYPE_MAP.items():
        row_id = (
            await db.execute(
                select(model.id).where(
                    model.project_id == project_id,
                    getattr(model, id_col_name) == public_id,
                )
            )
        ).scalar_one_or_none()
        if row_id is not None:
            return type_code, row_id
    return None


MAX_DOC_KEYS = 500


def _parse_doc_keys(keys: list[str]) -> set[tuple[str, int]]:
    """Parse ``TYPE:row_id`` pairs into the key set the union filters on.

    The Document-backed kinds count as known types beside TYPE_MAP.
    """
    parsed: set[tuple[str, int]] = set()
    for key in keys:
        type_code, _, raw_id = key.partition(":")
        type_code = type_code.strip().upper()
        if type_code not in TYPE_MAP and type_code not in CANONICAL_DOCUMENT_KINDS:
            raise HTTPException(status_code=422, detail=f"Unknown document type in key '{key}'")
        try:
            parsed.add((type_code, int(raw_id)))
        except ValueError:
            raise HTTPException(
                status_code=422, detail=f"Key '{key}' is not of the form TYPE:id"
            ) from None
    return parsed


async def _related_doc_keys(
    db: AsyncSession,
    project_id: int,
    anchor: tuple[str, int],
    role: Optional[str],
    direction: Optional[str],
) -> set[tuple[str, int]]:
    """Every (type_code, row id) sharing a relationship with the anchor document."""
    anchor_type, anchor_id = anchor
    related: set[tuple[str, int]] = set()

    if direction in (None, "", "outgoing"):
        query = select(ArtefactLink.target_type, ArtefactLink.target_id).where(
            ArtefactLink.project_id == project_id,
            ArtefactLink.source_type == anchor_type,
            ArtefactLink.source_id == anchor_id,
        )
        if role:
            query = query.where(ArtefactLink.role == role)
        related.update((t, i) for t, i in (await db.execute(query)).all())

    if direction in (None, "", "incoming"):
        query = select(ArtefactLink.source_type, ArtefactLink.source_id).where(
            ArtefactLink.project_id == project_id,
            ArtefactLink.target_type == anchor_type,
            ArtefactLink.target_id == anchor_id,
        )
        if role:
            query = query.where(ArtefactLink.role == role)
        related.update((t, i) for t, i in (await db.execute(query)).all())

    return related


_TYPE_LABELS = {
    "REQ": "Requirement",
    "TC": "Test Case",
    "DES": "Design",
    "RSK": "Risk",
    "CHG": "Change Request",
    "CPT": "Test Concept",
    "DEF": "Defect",
    "CMP": "Campaign",
    "TS": "Test Suite",
    "SPEC": "Specification",
    "PRT": "Protocol",
    "RPT": "Report",
    "STD": "External Standard",
    "VIS": "Vision",
}

_SORT_FIELDS = frozenset(
    {
        "updated_at",
        "created_at",
        "doc_id",
        "doc_type",
        "status",
        "title",
        "priority",
        "req_type",
        "req_origin",
        "reviewer",
    }
)

_LINK_FILTERS = frozenset({"linked", "unlinked", "incoming", "outgoing", "suspect", "clean"})


def _optional_column(model, name: str, type_):
    """The model's column, or a typed NULL for the arms that do not have one."""
    column = getattr(model, name, None)
    return cast(null(), type_) if column is None else column


def _shell_arm(model, type_code: str, id_col_name: str):
    """One type's contribution to the registry union: shell columns, nothing else.

    A row without a public id is shown as `TYPE-<row id>`.
    """
    id_col = getattr(model, id_col_name)
    title_col = model.title if hasattr(model, "title") else model.name

    if hasattr(model, "priority"):
        priority_col = model.priority
    elif hasattr(model, "severity"):
        priority_col = model.severity
    else:
        priority_col = cast(null(), String)

    status_col = model.status
    if type_code in CONTROLLED_TYPES:
        phase = func.coalesce(
            ArtefactWorkflow.phase,
            case(
                {phase.lower(): phase for phase in WORKFLOW_PHASES},
                value=func.lower(func.trim(model.status)),
                else_=null(),
            ),
        )
        status_col = (
            case((model.status.in_(LEGACY_CHANGE_STATUSES), model.status), else_=phase)
            if type_code == "CHG"
            else phase
        )
    query = select(
        model.id.label("row_id"),
        func.coalesce(
            cast(id_col, String),
            literal(f"{type_code}-", String) + cast(model.id, String),
        ).label("doc_id"),
        literal(type_code).label("doc_type"),
        title_col.label("title"),
        status_col.label("status"),
        model.visibility.label("visibility"),
        priority_col.label("priority"),
        _optional_column(model, "req_type", String).label("req_type"),
        _optional_column(model, "req_origin", String).label("req_origin"),
        _optional_column(model, "reviewer_id", Integer).label("reviewer_id"),
        _optional_column(model, "last_execution_status", String).label("last_execution_status"),
        _optional_column(model, "last_executed_at", DateTime).label("last_executed_at"),
        _optional_column(model, "last_bud_run_id", Integer).label("last_bud_run_id"),
        model.created_at.label("created_at"),
        model.updated_at.label("updated_at"),
    )
    if type_code in CONTROLLED_TYPES:
        slug = TAG_TYPE_OF_MODEL[model]
        query = query.outerjoin(
            ArtefactWorkflow,
            and_(
                ArtefactWorkflow.artefact_type == slug,
                ArtefactWorkflow.artefact_id == model.id,
                ArtefactWorkflow.project_id == model.project_id,
            ),
        )
    return query


def _link_count_subqueries(project_id: int, types: frozenset[str] | None = None):
    """Per-document incoming and outgoing link tallies, as two grouped subqueries, counting
    only links whose other end is of a type in ``types`` (None: every type)."""
    suspect_sum = func.coalesce(
        func.sum(case((ArtefactLink.suspect.is_(True), 1), else_=0)), 0
    ).label("suspect_count")

    incoming = (
        select(
            ArtefactLink.target_type.label("owner_type"),
            ArtefactLink.target_id.label("owner_id"),
            func.count().label("link_count"),
            suspect_sum,
        )
        .where(
            ArtefactLink.project_id == project_id,
            true() if types is None else ArtefactLink.source_type.in_(types),
        )
        .group_by(ArtefactLink.target_type, ArtefactLink.target_id)
        .subquery("incoming_links")
    )
    outgoing = (
        select(
            ArtefactLink.source_type.label("owner_type"),
            ArtefactLink.source_id.label("owner_id"),
            func.count().label("link_count"),
            suspect_sum,
        )
        .where(
            ArtefactLink.project_id == project_id,
            true() if types is None else ArtefactLink.target_type.in_(types),
        )
        .group_by(ArtefactLink.source_type, ArtefactLink.source_id)
        .subquery("outgoing_links")
    )
    return incoming, outgoing


def _registry_union(
    project: Project,
    current_user: User,
    *,
    type_filter: Optional[list[str]],
    related_keys: Optional[set[tuple[str, int]]],
    types: frozenset[str] | None,
):
    """The set of documents of the ``types`` (from `visible_types`) this user may see in
    this project, as one union.

    The shared Document table contributes one arm per document kind.
    """
    arms = []

    for type_code, (model, id_col_name, _slug) in TYPE_MAP.items():
        if type_filter and type_code not in type_filter:
            continue
        if not type_visible(types, type_code):
            continue

        allowed_ids = None
        if related_keys is not None:
            allowed_ids = [rid for tcode, rid in related_keys if tcode == type_code]
            if not allowed_ids:
                continue

        arm = _shell_arm(model, type_code, id_col_name).where(model.project_id == project.id)
        if allowed_ids is not None:
            arm = arm.where(model.id.in_(allowed_ids))
        arms.append(apply_external_visibility_filter(arm, model, current_user))

    document_kinds = [
        kind
        for kind in (type_filter if type_filter else CANONICAL_DOCUMENT_KINDS)
        if kind in CANONICAL_DOCUMENT_KINDS
    ]
    document_kinds = [kind for kind in document_kinds if type_visible(types, kind)]

    for kind in document_kinds:
        allowed_ids = None
        if related_keys is not None:
            allowed_ids = [rid for tcode, rid in related_keys if tcode == kind]
            if not allowed_ids:
                continue

        arm = _shell_arm(Document, kind, "doc_id").where(
            Document.project_id == project.id,
            Document.doc_type == kind,
        )
        if allowed_ids is not None:
            arm = arm.where(Document.id.in_(allowed_ids))
        arms.append(apply_external_visibility_filter(arm, Document, current_user))

    if not arms:
        return None
    return union_all(*arms).subquery("registry")


@router.get(
    "/projects/{project_ref}/docs",
    response_model=PaginatedResponse[DocShellResponse],
    responses={404: {"description": "Not Found"}, 422: {"description": "Unprocessable Content"}},
)
async def list_all_docs(
    project_ref: str,
    type: Optional[List[str]] = Query(None),
    status: Optional[List[str]] = Query(None),
    q: Optional[str] = None,
    priority: Optional[str] = None,
    reviewer: Optional[str] = Query(
        None,
        description="A user id, or `assigned` / `unassigned` for documents with and without one.",
    ),
    links: Optional[str] = Query(
        None,
        pattern="^(linked|unlinked|incoming|outgoing|suspect|clean)$",
        description="Restrict to documents by how they are linked.",
    ),
    created_from: Optional[date] = None,
    created_to: Optional[date] = None,
    updated_from: Optional[date] = None,
    updated_to: Optional[date] = None,
    sort: str = Query("updated_at", description="One of the registry's sortable columns."),
    dir: str = Query("desc", pattern="^(asc|desc)$"),
    related_to: Optional[str] = Query(
        None,
        description="Only documents sharing a relationship with this document id (e.g. PRJ-REQ-001).",
    ),
    keys: Optional[List[str]] = Query(
        None,
        description="Only these documents, as `TYPE:row_id` pairs (e.g. `REQ:12`).",
    ),
    role: Optional[str] = Query(
        None, description="Restrict `related_to` to a single relationship role."
    ),
    direction: Optional[str] = Query(
        None,
        pattern="^(incoming|outgoing)$",
        description="Restrict `related_to` to one direction of the relationship.",
    ),
    include_link_counts: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int | None = Query(None, ge=1, le=500),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """List all docs across all types for a project.

    related_to and anchor filters together keep the documents that satisfy both; a link filter joins
    the link counts also when they are not requested; search covers the kind label and the reviewer
    name besides the stored fields; the row id breaks ties in the ordering for stable pages.
    """
    project = await resolve_project(db, project_ref)
    await require_project_access(db, current_user, project.id)

    if sort not in _SORT_FIELDS:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot sort by '{sort}'. Sortable: {', '.join(sorted(_SORT_FIELDS))}.",
        )

    type_filter = [t.upper() for t in type] if type else None
    empty = PaginatedResponse(items=[], total=0, skip=skip, limit=limit or 0)

    related_keys: set[tuple[str, int]] | None = None
    if keys is not None:
        if len(keys) > MAX_DOC_KEYS:
            raise HTTPException(
                status_code=422,
                detail=f"Ask for at most {MAX_DOC_KEYS} documents at a time, not {len(keys)}.",
            )
        related_keys = _parse_doc_keys(keys)
        if not related_keys:
            return empty
    if related_to:
        anchor = await _resolve_doc_by_public_id(db, project.id, related_to.strip().upper())
        if anchor is None:
            raise HTTPException(status_code=404, detail=f"Document {related_to} not found")
        anchor_keys = await _related_doc_keys(db, project.id, anchor, role, direction)
        related_keys = anchor_keys if related_keys is None else related_keys & anchor_keys
        if not related_keys:
            return empty

    types = await visible_types(db, current_user, project.id)
    registry = _registry_union(
        project,
        current_user,
        type_filter=type_filter,
        related_keys=related_keys,
        types=types,
    )
    if registry is None:
        return empty

    want_counts = include_link_counts or links is not None
    if want_counts:
        incoming, outgoing = _link_count_subqueries(project.id, types)
        incoming_links = func.coalesce(incoming.c.link_count, 0)
        outgoing_links = func.coalesce(outgoing.c.link_count, 0)
        suspect_links = func.coalesce(incoming.c.suspect_count, 0) + func.coalesce(
            outgoing.c.suspect_count, 0
        )
    else:
        incoming = outgoing = None
        incoming_links = outgoing_links = suspect_links = literal(0)

    reviewer_user = aliased(User)
    reviewer_name = func.coalesce(reviewer_user.full_name, "")

    query = select(
        registry,
        incoming_links.label("incoming_links"),
        outgoing_links.label("outgoing_links"),
        suspect_links.label("suspect_links"),
    ).select_from(registry)

    if want_counts:
        query = query.outerjoin(
            incoming,
            and_(
                incoming.c.owner_type == registry.c.doc_type,
                incoming.c.owner_id == registry.c.row_id,
            ),
        ).outerjoin(
            outgoing,
            and_(
                outgoing.c.owner_type == registry.c.doc_type,
                outgoing.c.owner_id == registry.c.row_id,
            ),
        )

    needs_reviewer_name = sort == "reviewer" or bool(q and q.strip())
    if needs_reviewer_name:
        query = query.outerjoin(reviewer_user, reviewer_user.id == registry.c.reviewer_id)

    if status:
        query = query.where(registry.c.status.in_(status))
    if priority:
        query = query.where(func.coalesce(registry.c.priority, "") == priority)

    if reviewer == "assigned":
        query = query.where(registry.c.reviewer_id.is_not(None))
    elif reviewer == "unassigned":
        query = query.where(registry.c.reviewer_id.is_(None))
    elif reviewer:
        if not reviewer.isdigit():
            raise HTTPException(
                status_code=422,
                detail="reviewer must be a user id, `assigned` or `unassigned`.",
            )
        query = query.where(registry.c.reviewer_id == int(reviewer))

    if created_from:
        query = query.where(registry.c.created_at >= datetime.combine(created_from, time.min))
    if created_to:
        query = query.where(registry.c.created_at <= datetime.combine(created_to, time.max))
    if updated_from:
        query = query.where(registry.c.updated_at >= datetime.combine(updated_from, time.min))
    if updated_to:
        query = query.where(registry.c.updated_at <= datetime.combine(updated_to, time.max))

    if links == "linked":
        query = query.where(incoming_links + outgoing_links > 0)
    elif links == "unlinked":
        query = query.where(incoming_links + outgoing_links == 0)
    elif links == "incoming":
        query = query.where(incoming_links > 0)
    elif links == "outgoing":
        query = query.where(outgoing_links > 0)
    elif links == "suspect":
        query = query.where(suspect_links > 0)
    elif links == "clean":
        query = query.where(suspect_links == 0)

    if q and q.strip():
        needle = f"%{q.strip()}%"
        type_label = case(
            *[(registry.c.doc_type == code, label) for code, label in _TYPE_LABELS.items()],
            else_=registry.c.doc_type,
        )
        query = query.where(
            or_(
                registry.c.doc_id.ilike(needle),
                registry.c.title.ilike(needle),
                registry.c.doc_type.ilike(needle),
                type_label.ilike(needle),
                registry.c.status.ilike(needle),
                func.coalesce(registry.c.priority, "").ilike(needle),
                func.coalesce(registry.c.req_type, "").ilike(needle),
                func.coalesce(registry.c.req_origin, "").ilike(needle),
                reviewer_name.ilike(needle),
                cast(registry.c.created_at, String).ilike(needle),
                cast(registry.c.updated_at, String).ilike(needle),
            )
        )

    total = (
        await db.execute(select(func.count()).select_from(query.subquery("matched")))
    ).scalar_one()

    sort_columns = {
        "updated_at": registry.c.updated_at,
        "created_at": registry.c.created_at,
        "doc_id": func.lower(registry.c.doc_id),
        "doc_type": func.lower(registry.c.doc_type),
        "status": func.lower(registry.c.status),
        "title": func.lower(registry.c.title),
        "priority": func.lower(func.coalesce(registry.c.priority, "")),
        "req_type": func.lower(func.coalesce(registry.c.req_type, "")),
        "req_origin": func.lower(func.coalesce(registry.c.req_origin, "")),
        "reviewer": func.lower(reviewer_name) if needs_reviewer_name else literal(""),
    }
    order = sort_columns[sort]
    query = query.order_by(
        order.desc() if dir == "desc" else order.asc(),
        registry.c.doc_type,
        registry.c.row_id,
    )

    if limit is not None:
        query = query.offset(skip).limit(limit)

    rows = (await db.execute(query)).all()
    items = [
        DocShellResponse(
            id=row.row_id,
            doc_id=row.doc_id,
            doc_type=row.doc_type,
            title=row.title,
            status=row.status,
            visibility=row.visibility,
            priority=row.priority,
            req_type=row.req_type,
            req_origin=row.req_origin,
            project_id=project.id,
            reviewer_id=row.reviewer_id,
            incoming_links=row.incoming_links,
            outgoing_links=row.outgoing_links,
            suspect_links=row.suspect_links,
            last_execution_status=row.last_execution_status,
            last_executed_at=row.last_executed_at,
            last_bud_run_id=row.last_bud_run_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]

    if limit is None:
        return PaginatedResponse(items=items, total=total, skip=0, limit=total)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


class DocTypeCount(BaseModel):
    doc_type: str
    count: int
    suspect_links: int


class MembershipEdge(BaseModel):
    source_type: str
    target_type: str
    role: str
    count: int


class DocTypeSummaryResponse(BaseModel):
    types: List[DocTypeCount]
    total: int
    membership_edges: List[MembershipEdge] = []


@router.get(
    "/projects/{project_ref}/doc-type-summary",
    response_model=DocTypeSummaryResponse,
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def get_doc_type_summary(
    project_ref: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """How many documents of each type this user can see, and how many suspect links."""
    project = await resolve_project(db, project_ref)
    await require_project_access(db, current_user, project.id)

    visible = await visible_types(db, current_user, project.id)
    registry = _registry_union(
        project, current_user, type_filter=None, related_keys=None, types=visible
    )
    if registry is None:
        return DocTypeSummaryResponse(types=[], total=0, membership_edges=[])

    incoming, outgoing = _link_count_subqueries(project.id, visible)
    suspect_links = func.coalesce(incoming.c.suspect_count, 0) + func.coalesce(
        outgoing.c.suspect_count, 0
    )

    query = (
        select(
            registry.c.doc_type,
            func.count().label("doc_count"),
            func.coalesce(func.sum(suspect_links), 0).label("suspect_total"),
        )
        .select_from(registry)
        .outerjoin(
            incoming,
            and_(
                incoming.c.owner_type == registry.c.doc_type,
                incoming.c.owner_id == registry.c.row_id,
            ),
        )
        .outerjoin(
            outgoing,
            and_(
                outgoing.c.owner_type == registry.c.doc_type,
                outgoing.c.owner_id == registry.c.row_id,
            ),
        )
        .group_by(registry.c.doc_type)
    )

    rows = (await db.execute(query)).all()
    types = [
        DocTypeCount(
            doc_type=row.doc_type, count=row.doc_count, suspect_links=int(row.suspect_total)
        )
        for row in rows
    ]
    return DocTypeSummaryResponse(
        types=types,
        total=sum(t.count for t in types),
        membership_edges=await _membership_edges(db, project.id, visible),
    )


async def _membership_edges(
    db: AsyncSession, project_id: int, types: frozenset[str] | None
) -> List[MembershipEdge]:
    """How many suites are in campaigns and test cases in suites and campaigns, for the
    pairs whose two types are in ``types`` (None: every type)."""
    suites_in_campaigns = (
        select(func.count())
        .select_from(CampaignSuite)
        .join(TestCampaign, TestCampaign.id == CampaignSuite.campaign_id)
        .where(TestCampaign.project_id == project_id)
    )
    cases_in_suites = (
        select(func.count())
        .select_from(TestSuiteItem)
        .join(TestSuite, TestSuite.id == TestSuiteItem.suite_id)
        .where(TestSuite.project_id == project_id)
    )
    cases_in_campaigns = (
        select(func.count())
        .select_from(TestCampaignItem)
        .join(TestCampaign, TestCampaign.id == TestCampaignItem.campaign_id)
        .where(TestCampaign.project_id == project_id)
    )

    counted = [
        ("CMP", "TS", "relates_to", await db.scalar(suites_in_campaigns)),
        ("TS", "TC", "contains", await db.scalar(cases_in_suites)),
        ("CMP", "TC", "contains", await db.scalar(cases_in_campaigns)),
    ]
    return [
        MembershipEdge(source_type=source, target_type=target, role=role, count=count)
        for source, target, role, count in counted
        if count and type_visible(types, source) and type_visible(types, target)
    ]


class NextDocIdResponse(BaseModel):
    next_id: str


_DOCUMENT_TYPE_CODES = {"SPEC", "PRT", "RPT", "STD", "VIS"}


@router.get(
    "/projects/{project_ref}/next-doc-id/{type_code}",
    response_model=NextDocIdResponse,
    responses={
        400: {"description": HTTPStatus(400).phrase},
        404: {"description": HTTPStatus(404).phrase},
    },
)
async def get_next_doc_id(
    project_ref: str,
    type_code: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Report the identifier the server would assign to the next document."""
    project = await resolve_project(db, project_ref)
    await require_project_access(db, current_user, project.id)

    code = type_code.upper()
    if code in TYPE_MAP:
        model, id_field, _slug = TYPE_MAP[code]
        id_column = getattr(model, id_field)
    elif code in _DOCUMENT_TYPE_CODES:
        model, id_column = Document, Document.doc_id
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported document type: {type_code}")
    if not type_visible(await visible_types(db, current_user, project.id), code):
        raise HTTPException(status_code=400, detail=f"Unsupported document type: {type_code}")

    try:
        next_id = await next_doc_id(db, model, id_column, project.id, project.prefix, code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return NextDocIdResponse(next_id=next_id)


async def _reference_query(db: AsyncSession, model, id_col, project_id: int, ref: str, *conditions):
    """The unfiltered query for one item of a kind in a project by its document ID, or by its
    database id when the reference is a number that no item of that kind has as document ID."""
    base = select(model).where(model.project_id == project_id, *conditions)
    by_doc_id = base.where(id_col == ref)
    if ref.isdigit():
        found = (await db.execute(by_doc_id.with_only_columns(model.id))).first()
        if found is None:
            return base.where(model.id == int(ref))
    return by_doc_id


async def _visible_row(
    db, user, project_id, unfiltered, model, type_code, view_type, *, allowed, record
):
    """The row of the unfiltered query and its document type when the user may see it, else
    None; with record, a hidden row marks the request as a refusal."""
    if not external_doc_type_allowed(allowed, type_code):
        if record:
            await mark_refused_if_found(db, unfiltered)
        return None
    row = (
        await db.execute(apply_external_visibility_filter(unfiltered, model, user))
    ).scalar_one_or_none()
    if row is None:
        if record:
            await mark_refused_if_found(db, unfiltered)
        return None
    resolved_type = view_type(row)
    if not await holds(db, user, project_id, "view", resolved_type):
        if record:
            mark_refused()
        return None
    return row, resolved_type


async def find_visible_doc(
    db: AsyncSession,
    current_user: User,
    project: Project,
    kind_slug: str,
    ref: str,
    *,
    record_refusals: bool = True,
):
    """The item of a kind slug in a project that the user may see, by document ID or database
    id, as (model, row, resolved type code, document ID column), or None.

    With record_refusals, a hidden item marks the request as a refusal for the audit log.
    """
    kind_slug = LEGACY_TYPE_SLUG_ALIASES.get(kind_slug, kind_slug)
    allowed_doc_types = await get_external_doc_types(db, current_user, project.id)
    checks = {"allowed": allowed_doc_types, "record": record_refusals}
    if kind_slug not in {slug for _, (_, _, slug) in TYPE_MAP.items()}:
        requested_kind = document_kind_from_slug(kind_slug)
        if requested_kind not in CANONICAL_DOCUMENT_KINDS:
            return None
        unfiltered = await _reference_query(
            db, Document, Document.doc_id, project.id, ref, Document.doc_type == requested_kind
        )
        found = await _visible_row(
            db,
            current_user,
            project.id,
            unfiltered,
            Document,
            requested_kind,
            lambda _row: requested_kind,
            **checks,
        )
        return (Document, found[0], requested_kind, "doc_id") if found else None

    for type_code, (model, id_col_name, slug) in TYPE_MAP.items():
        if slug != kind_slug:
            continue
        unfiltered = await _reference_query(db, model, getattr(model, id_col_name), project.id, ref)
        found = await _visible_row(
            db,
            current_user,
            project.id,
            unfiltered,
            model,
            type_code,
            lambda row, code=type_code: _resolved_doc_type(code, row),
            **checks,
        )
        if found:
            return model, found[0], found[1], id_col_name
    return None


@router.get(
    "/projects/{project_ref}/docs/{kind_slug}/{doc_id_str}",
    response_model=DocDetailFacadeResponse,
    responses={404: {"description": HTTPStatus(404).phrase}},
)
async def get_doc_by_kind_and_string_id(
    project_ref: str,
    kind_slug: str,
    doc_id_str: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """Look up a doc by its kind-aware slug and its document ID, or its database id."""
    project = await resolve_project(db, project_ref)
    await require_project_access(db, current_user, project.id)
    found = await find_visible_doc(db, current_user, project, kind_slug, doc_id_str)
    if found is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Document '{doc_id_str}' with kind '{kind_slug}' "
                f"not found in project '{project.prefix}'"
            ),
        )
    model, row, resolved_type, id_col_name = found
    link_data = (
        await _count_links(
            db,
            project.id,
            resolved_type,
            [row.id],
            await visible_types(db, current_user, project.id),
        )
    ).get(row.id, {"incoming": 0, "outgoing": 0, "suspect": 0})
    return DocDetailFacadeResponse(
        id=row.id,
        doc_id=str(getattr(row, id_col_name) or row.id),
        doc_type=resolved_type,
        title=row.title if hasattr(row, "title") else row.name,
        status=await current_status(db, row),
        visibility=getattr(row, "visibility", ArtefactVisibility.internal.value),
        priority=_get_priority(model, row),
        project_id=project.id,
        reviewer_id=_get_reviewer_id(model, row),
        incoming_links=link_data["incoming"],
        outgoing_links=link_data["outgoing"],
        suspect_links=link_data["suspect"],
        description=getattr(row, "description", None),
        content_json=getattr(row, "content_json", None),
        content_html=getattr(row, "content_html", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
        allowed_actions=await allowed_actions(db, current_user, row, resolved_type),
    )
