"""
Unified docs facade: PLM-style lookup by string doc_id across all type tables,
and a unified list endpoint for all doc types within a project.
"""

from datetime import date, datetime, time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
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
    union_all,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

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
    UserRole,
)
from app.models.user import User
from app.schemas import PaginatedResponse

router = APIRouter()


class DocShellResponse(BaseModel):
    id: int
    doc_id: str
    doc_type: str
    title: str
    status: str
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


class DocDetailFacadeResponse(DocShellResponse):
    description: str | None = None
    content_json: dict | None = None
    content_html: str | None = None


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
    db: AsyncSession, project_id: int, type_code: str, row_ids: list[int]
) -> dict[int, dict]:
    """Return {row_id: {incoming, outgoing, suspect}} for the given rows."""
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
    """Resolve a human-readable id such as ``FLT-REQ-001`` to (type_code, row id)."""
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
    """Parse ``TYPE:row_id`` pairs into the key set the union already filters on.

    A caller that holds links holds (type, row id) pairs, not public ids - that
    is what a link stores. Letting it ask for exactly those documents is what
    keeps a panel showing a dozen chips from reading the whole project to find
    a dozen titles.
    """
    parsed: set[tuple[str, int]] = set()
    for key in keys:
        type_code, _, raw_id = key.partition(":")
        type_code = type_code.strip().upper()
        # The four Document-backed kinds are not in TYPE_MAP but are perfectly
        # good link targets, so both families count as known.
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


# ---------------------------------------------------------------------------
# The registry listing
#
# This used to run `select(model)` against every type table and finish the job
# in Python. `select(model)` is whole rows, so `description`, `content_json`
# and `content_html` came back for every document and were then discarded -
# DocShellResponse carries none of them. The browser then received the entire
# project and did the filtering, sorting and paging a second time.
#
# Now each type contributes one arm of a UNION ALL carrying only the columns
# the shell actually has, and filtering, sorting and paging happen in SQL over
# that union. Callers that pass no filters and no limit get exactly what they
# got before, so the topology's paged fetch is unaffected.
# ---------------------------------------------------------------------------

# The labels the registry shows for each type. They live here as well as in the
# UI because free-text search matches what the reader can see: someone typing
# "Requirement" means the REQ rows, and the server is now the one searching.
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
    """The model's column, or a typed NULL for the arms that do not have one.

    Every arm of a UNION has to present the same columns in the same order, so a
    model without `req_origin` contributes a NULL of the right type rather than
    being left out. Only the NULL is given a type: SQLite's DATETIME has NUMERIC
    affinity, so casting a real timestamp column to it yields the year as an
    integer and the row comes back unreadable.
    """
    column = getattr(model, name, None)
    return cast(null(), type_) if column is None else column


def _shell_arm(model, type_code: str, id_col_name: str):
    """One type's contribution to the registry union: shell columns, nothing else."""
    id_col = getattr(model, id_col_name)
    title_col = model.title if hasattr(model, "title") else model.name

    if hasattr(model, "priority"):
        priority_col = model.priority
    elif hasattr(model, "severity"):
        priority_col = model.severity
    else:
        priority_col = cast(null(), String)

    return select(
        model.id.label("row_id"),
        # Campaigns may carry no campaign_id, and older documents no doc_id;
        # both used to fall back to "TYPE-<row id>" in Python.
        func.coalesce(
            cast(id_col, String),
            # `+` on a String-typed literal is the concatenation operator, which
            # both Postgres and the SQLite the tests run on spell `||`.
            literal(f"{type_code}-", String) + cast(model.id, String),
        ).label("doc_id"),
        literal(type_code).label("doc_type"),
        title_col.label("title"),
        model.status.label("status"),
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


def _link_count_subqueries(project_id: int):
    """Per-document incoming and outgoing link tallies, as two grouped subqueries.

    Joined onto the union rather than fetched per type, so the counts cost two
    grouped scans of `artefact_links` no matter how many types are in play, and
    stay filterable and sortable in SQL.
    """
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
        .where(ArtefactLink.project_id == project_id)
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
        .where(ArtefactLink.project_id == project_id)
        .group_by(ArtefactLink.source_type, ArtefactLink.source_id)
        .subquery("outgoing_links")
    )
    return incoming, outgoing


async def _registry_union(
    db: AsyncSession,
    project: Project,
    current_user: User,
    *,
    type_filter: Optional[list[str]],
    related_keys: Optional[set[tuple[str, int]]],
):
    """The set of documents this user may see in this project, as one union.

    Returns None when no type survives the filters, which is not the same as
    an empty result set: there is nothing to select from at all.
    """
    allowed_doc_types = await get_external_doc_types(db, current_user, project.id)
    arms = []

    for type_code, (model, id_col_name, _slug) in TYPE_MAP.items():
        if type_filter and type_code not in type_filter:
            continue
        if not external_doc_type_allowed(current_user, allowed_doc_types, type_code):
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

    # The shared Document table backs four types at once, so it contributes one
    # arm per kind rather than one arm overall.
    document_kinds = [
        kind
        for kind in (type_filter if type_filter else CANONICAL_DOCUMENT_KINDS)
        if kind in CANONICAL_DOCUMENT_KINDS
    ]
    if current_user.role == UserRole.external and allowed_doc_types is not None:
        document_kinds = [kind for kind in document_kinds if kind in allowed_doc_types]

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


@router.get("/projects/{project_ref}/docs", response_model=PaginatedResponse[DocShellResponse])
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
        description="Only documents sharing a relationship with this document id (e.g. FLT-REQ-001).",
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all docs across all types for a project."""
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
        # Both narrow to a key set, so asking for both means asking for the
        # documents that satisfy both.
        related_keys = anchor_keys if related_keys is None else related_keys & anchor_keys
        if not related_keys:
            return empty

    registry = await _registry_union(
        db,
        project,
        current_user,
        type_filter=type_filter,
        related_keys=related_keys,
    )
    if registry is None:
        return empty

    # A link filter is a question about the counts, so it needs them joined even
    # if the caller did not ask for the numbers themselves.
    want_counts = include_link_counts or links is not None
    if want_counts:
        incoming, outgoing = _link_count_subqueries(project.id)
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
        # The reader searches what the table shows them, so this covers the
        # human label of the kind and the reviewer's name as well as the stored
        # fields. Dates match on their ISO form - a timestamp cast to text
        # starts `YYYY-MM-DD` on Postgres and on the SQLite the tests run on,
        # so "2026-03" narrows to a month without a dialect-specific format.
        type_label = case(
            *[(registry.c.doc_type == code, label) for code, label in _TYPE_LABELS.items()],
            else_=registry.c.doc_type,
        )
        # One OR of ilikes rather than one ilike over a concatenation: the
        # concatenation has to be built for every row before it can be tested,
        # and it cannot use an index on any of the columns in it.
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
    # A tiebreaker, so page 2 cannot repeat a row page 1 already showed.
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


class DocTypeSummaryResponse(BaseModel):
    types: List[DocTypeCount]
    total: int


@router.get(
    "/projects/{project_ref}/doc-type-summary",
    response_model=DocTypeSummaryResponse,
)
async def get_doc_type_summary(
    project_ref: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """How many documents of each type this user can see, and how many suspect links.

    The topology draws one node per *type*, not per document, and the project
    screen wants a single count - both used to download every document in the
    project to work that out. This is the same numbers as one grouped query.

    Deliberately not routed under `/docs/...` so it cannot be mistaken for a
    document whose id happens to be "doc-type-summary".
    """
    project = await resolve_project(db, project_ref)
    await require_project_access(db, current_user, project.id)

    registry = await _registry_union(db, project, current_user, type_filter=None, related_keys=None)
    if registry is None:
        return DocTypeSummaryResponse(types=[], total=0)

    incoming, outgoing = _link_count_subqueries(project.id)
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
    return DocTypeSummaryResponse(types=types, total=sum(t.count for t in types))


class NextDocIdResponse(BaseModel):
    next_id: str


# Document-backed types share one table and are distinguished by doc_type.
_DOCUMENT_TYPE_CODES = {"SPEC", "PRT", "RPT", "STD"}


@router.get("/projects/{project_ref}/next-doc-id/{type_code}", response_model=NextDocIdResponse)
async def get_next_doc_id(
    project_ref: str,
    type_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Report the identifier the server would assign to the next document.

    The create screen used to render a hardcoded ``-001`` preview, which claimed
    an identifier that was usually already taken. The server allocates with
    MAX(suffix)+1, so the preview has to come from the same place.

    Deliberately not routed under ``/docs/{kind_slug}/...`` so it cannot be
    mistaken for a document whose id happens to be "next-doc-id".
    """
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

    try:
        next_id = await next_doc_id(db, model, id_column, project.id, project.prefix, code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return NextDocIdResponse(next_id=next_id)


@router.get(
    "/projects/{project_ref}/docs/{kind_slug}/{doc_id_str}", response_model=DocDetailFacadeResponse
)
async def get_doc_by_kind_and_string_id(
    project_ref: str,
    kind_slug: str,
    doc_id_str: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Look up a doc by its kind-aware slug and human-readable string ID."""
    project = await resolve_project(db, project_ref)
    await require_project_access(db, current_user, project.id)
    kind_slug = LEGACY_TYPE_SLUG_ALIASES.get(kind_slug, kind_slug)
    requested_kind = None
    if kind_slug in {slug for _, (_, _, slug) in TYPE_MAP.items()}:
        pass
    else:
        requested_kind = document_kind_from_slug(kind_slug)

    allowed_doc_types = await get_external_doc_types(db, current_user, project.id)

    if requested_kind in CANONICAL_DOCUMENT_KINDS:
        if not external_doc_type_allowed(current_user, allowed_doc_types, requested_kind):
            raise HTTPException(status_code=404, detail="Document not found")
        document_query = select(Document).where(
            Document.project_id == project.id,
            Document.doc_type == requested_kind,
            Document.doc_id == doc_id_str,
        )
        document_query = apply_external_visibility_filter(document_query, Document, current_user)
        result = await db.execute(document_query)
        row = result.scalar_one_or_none()
        if row:
            link_data = (await _count_links(db, project.id, requested_kind, [row.id])).get(
                row.id, {"incoming": 0, "outgoing": 0, "suspect": 0}
            )
            return DocDetailFacadeResponse(
                id=row.id,
                doc_id=row.doc_id,
                doc_type=requested_kind,
                title=row.title,
                status=row.status,
                visibility=row.visibility,
                priority=_get_priority(Document, row),
                project_id=project.id,
                reviewer_id=_get_reviewer_id(Document, row),
                incoming_links=link_data["incoming"],
                outgoing_links=link_data["outgoing"],
                suspect_links=link_data["suspect"],
                description=row.description,
                content_json=row.content_json,
                content_html=row.content_html,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
    else:
        for type_code, (model, id_col_name, slug) in TYPE_MAP.items():
            if slug != kind_slug:
                continue

            if not external_doc_type_allowed(current_user, allowed_doc_types, type_code):
                continue
            id_col = getattr(model, id_col_name)
            if id_col_name == "id":
                try:
                    id_filter = model.id == int(doc_id_str)
                except ValueError:
                    continue
            else:
                id_filter = id_col == doc_id_str
            typed_query = select(model).where(
                model.project_id == project.id,
                id_filter,
            )
            typed_query = apply_external_visibility_filter(typed_query, model, current_user)
            result = await db.execute(typed_query)
            row = result.scalar_one_or_none()
            if row:
                doc_id_val = getattr(row, id_col_name)
                title_val = row.title if hasattr(row, "title") else row.name
                desc_val = row.description if hasattr(row, "description") else None
                cj = row.content_json if hasattr(row, "content_json") else None
                ch = row.content_html if hasattr(row, "content_html") else None
                resolved_type = _resolved_doc_type(type_code, row)
                lc = await _count_links(db, project.id, resolved_type, [row.id])
                link_data = lc.get(row.id, {"incoming": 0, "outgoing": 0, "suspect": 0})

                return DocDetailFacadeResponse(
                    id=row.id,
                    doc_id=str(doc_id_val),
                    doc_type=resolved_type,
                    title=title_val,
                    status=row.status,
                    visibility=getattr(row, "visibility", ArtefactVisibility.internal.value),
                    priority=_get_priority(model, row),
                    project_id=project.id,
                    reviewer_id=_get_reviewer_id(model, row),
                    incoming_links=link_data["incoming"],
                    outgoing_links=link_data["outgoing"],
                    suspect_links=link_data["suspect"],
                    description=desc_val,
                    content_json=cj,
                    content_html=ch,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )

    raise HTTPException(
        status_code=404,
        detail=(
            f"Document '{doc_id_str}' with kind '{kind_slug}' "
            f"not found in project '{project.prefix}'"
        ),
    )
