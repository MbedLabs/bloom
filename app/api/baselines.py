"""Baselines API endpoints."""

from datetime import date, datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.api.artefact_utils import (
    apply_update,
    delete_project_row,
    fully_visible_types,
    get_row_or_404,
    get_visible_row,
    holds,
    type_visible,
)
from app.core.database import get_db
from app.core.document_kinds import CANONICAL_DOCUMENT_KINDS
from app.core.id_generator import next_doc_id
from app.core.link_rules import normalize_linkable_type
from app.core.security import (
    apply_external_visibility_filter,
    get_current_user,
    require_project_access,
)
from app.models import (
    ArtefactLink,
    Baseline,
    ChangeRequest,
    DesignItem,
    Document,
    DocumentSection,
    Project,
    ProjectVariable,
    Requirement,
    RequirementLink,
    RiskItem,
    TestCase,
)
from app.models.user import User, UserRole
from app.schemas import BaselineCreate, BaselineResponse, BaselineUpdate
from app.services.audit import record_audit_event

BASELINE_NOT_FOUND = "Baseline not found"

SNAPSHOT_SCHEMA_VERSION = 2

router = APIRouter()

SNAPSHOT_SECTION_TYPES = {
    "requirements": ("REQ",),
    "test_cases": ("TC",),
    "documents": ("SPEC", "PRT", "RPT", "STD"),
    "designs": ("DES",),
    "risks": ("RSK",),
    "changes": ("CHG",),
    "visions": ("VIS",),
}

RECORD_SECTIONS = {
    "requirements": ("requirements", "ids", "req_id"),
    "test_cases": ("test_cases", "ids", "tc_id"),
    "documents": ("documents", "titles", "title"),
    "designs": ("design_items", "ids", "design_id"),
    "risks": ("risk_items", "ids", "risk_id"),
    "changes": ("change_requests", "ids", "change_id"),
    "visions": ("documents", "ids", "doc_id"),
}

RECORD_MODELS = {
    "requirements": Requirement,
    "test_cases": TestCase,
    "documents": Document,
    "design_items": DesignItem,
    "risk_items": RiskItem,
    "change_requests": ChangeRequest,
}

RELATED_KEYS = ("document_sections", "project_variables", "requirement_links", "artefact_links")

LINK_ENDPOINT_TABLES = {
    "REQ": "requirements",
    "TC": "test_cases",
    "DES": "design_items",
    "RSK": "risk_items",
    "CHG": "change_requests",
    **{kind: "documents" for kind in CANONICAL_DOCUMENT_KINDS},
}


def _json_value(value):
    """A column value as JSON: timestamps as ISO 8601 UTC strings, dates as ISO 8601 dates,
    enumerations as their values, every other value unchanged."""
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


async def _records(connection, statement) -> list[dict]:
    """The rows of a statement over one table as dictionaries of their persisted columns."""
    rows = (await connection.execute(statement)).mappings().all()
    return [{key: _json_value(value) for key, value in row.items()} for row in rows]


def _link_endpoint_table(link_type: str | None) -> str | None:
    """The captured table an artefact link endpoint type points into, or None for a type
    the snapshot does not capture."""
    return LINK_ENDPOINT_TABLES.get(normalize_linkable_type(link_type))


def _captured_artefact_links(links: list[dict], captured: dict[str, set[int]]) -> list[dict]:
    """The artefact links whose source and target are both captured records."""

    def captured_endpoint(link_type, record_id) -> bool:
        table = _link_endpoint_table(link_type)
        return table is not None and record_id in captured.get(table, set())

    return [
        link
        for link in links
        if captured_endpoint(link["source_type"], link["source_id"])
        and captured_endpoint(link["target_type"], link["target_id"])
    ]


async def _capture(connection, project_id: int) -> dict:
    """The project's captured rows: the six artefact tables, the sections of its documents,
    its parameters, the requirement links between its requirements and the artefact links
    between its captured records."""
    by_id = {}
    for table_key, model in RECORD_MODELS.items():
        by_id[table_key] = await _records(
            connection,
            select(model.__table__).where(model.project_id == project_id).order_by(model.id),
        )
    project_documents = select(Document.id).where(Document.project_id == project_id)
    project_requirements = select(Requirement.id).where(Requirement.project_id == project_id)
    by_id["document_sections"] = await _records(
        connection,
        select(DocumentSection.__table__)
        .where(DocumentSection.document_id.in_(project_documents))
        .order_by(DocumentSection.document_id, DocumentSection.order, DocumentSection.id),
    )
    by_id["project_variables"] = await _records(
        connection,
        select(ProjectVariable.__table__)
        .where(ProjectVariable.project_id == project_id)
        .order_by(ProjectVariable.kind, ProjectVariable.key, ProjectVariable.id),
    )
    by_id["requirement_links"] = await _records(
        connection,
        select(RequirementLink.__table__)
        .where(
            RequirementLink.source_id.in_(project_requirements),
            RequirementLink.target_id.in_(project_requirements),
        )
        .order_by(RequirementLink.id),
    )
    captured = {table: {record["id"] for record in by_id[table]} for table in RECORD_MODELS}
    by_id["artefact_links"] = _captured_artefact_links(
        await _records(
            connection,
            select(ArtefactLink.__table__)
            .where(ArtefactLink.project_id == project_id)
            .order_by(ArtefactLink.id),
        ),
        captured,
    )
    return by_id


async def _capture_consistently(db: AsyncSession, project_id: int) -> dict:
    """The captured rows, read on PostgreSQL in one repeatable-read transaction on a
    connection of its own, every table from the same database state; on another database,
    read in the request's session."""
    bind = db.bind
    if not isinstance(bind, AsyncEngine) or bind.dialect.name != "postgresql":
        return await _capture(db, project_id)
    async with bind.connect() as connection:
        repeatable = await connection.execution_options(isolation_level="REPEATABLE READ")
        async with repeatable.begin():
            return await _capture(repeatable, project_id)


def _category(records: list[dict], label: str, attribute: str) -> dict:
    """A category of the snapshot: the number of records, their public ids or titles and
    the records."""
    return {
        "count": len(records),
        label: [record[attribute] for record in records],
        "records": records,
    }


async def _build_snapshot(db: AsyncSession, project_id: int) -> dict:
    """The schema-versioned snapshot of the project: the time of capture, the seven
    categories with their count, ids or titles and records, and the captured sections,
    parameters and links."""
    captured_at = datetime.now(timezone.utc).isoformat()
    by_id = await _capture_consistently(db, project_id)
    rows = {
        section: by_id[table] for section, (table, _label, _attribute) in RECORD_SECTIONS.items()
    }
    rows["documents"] = [item for item in by_id["documents"] if item["doc_type"] != "VIS"]
    rows["visions"] = [item for item in by_id["documents"] if item["doc_type"] == "VIS"]
    snapshot: dict = {"schema_version": SNAPSHOT_SCHEMA_VERSION, "captured_at": captured_at}
    for section, (_table, label, attribute) in RECORD_SECTIONS.items():
        snapshot[section] = _category(rows[section], label, attribute)
    for key in RELATED_KEYS:
        snapshot[key] = {"records": by_id[key]}
    return snapshot


def _record_ids(section) -> list[int]:
    """The database ids of the records of a snapshot section."""
    if not isinstance(section, dict):
        return []
    return [
        record["id"]
        for record in section.get("records") or []
        if isinstance(record, dict) and isinstance(record.get("id"), int)
    ]


async def _live_ids(db: AsyncSession, query) -> set[int]:
    """The ids the query returns now."""
    return set((await db.execute(query)).scalars().all())


async def _readable_ids(db: AsyncSession, user: User, project_id: int) -> dict:
    """The ids of the project's rows the user may read now, per table: artefact rows that
    one of the user's terms there covers under their current visibility, document type and
    tags; parameters when the user holds view on parameters; the sections of the project's
    documents, the requirement links between its requirements and its artefact links, each
    further limited to shown endpoints by ``_filter_records``."""
    readable: dict[str, set[int]] = {}
    for table, model in RECORD_MODELS.items():
        readable[table] = await _live_ids(
            db,
            apply_external_visibility_filter(
                select(model.id).where(model.project_id == project_id), model, user
            ),
        )
    readable["project_variables"] = (
        await _live_ids(
            db, select(ProjectVariable.id).where(ProjectVariable.project_id == project_id)
        )
        if await holds(db, user, project_id, "view", "parameter")
        else set()
    )
    readable["document_sections"] = await _live_ids(
        db,
        select(DocumentSection.id).where(
            DocumentSection.document_id.in_(
                select(Document.id).where(Document.project_id == project_id)
            )
        ),
    )
    readable["requirement_links"] = await _live_ids(
        db,
        select(RequirementLink.id).where(
            RequirementLink.source_id.in_(
                select(Requirement.id).where(Requirement.project_id == project_id)
            )
        ),
    )
    readable["artefact_links"] = await _live_ids(
        db, select(ArtefactLink.id).where(ArtefactLink.project_id == project_id)
    )
    return readable


def _shown_section(value: dict, label: str, attribute: str, shown: set[int] | None) -> dict:
    """A category with only the records in ``shown`` (every record when None), its ids or
    titles taken from those records and its captured count kept."""
    records = [
        record
        for record in value.get("records") or []
        if shown is None or (isinstance(record, dict) and record.get("id") in shown)
    ]
    return {
        **value,
        label: [record.get(attribute) for record in records],
        "records": records,
    }


def _filter_records(snapshot: dict, readable: dict | None) -> dict:
    """The snapshot with each record kept when the user may read it now (every record when
    ``readable`` is None): a category record when readable, a section when its document is
    shown, a requirement link when both requirements are shown and an artefact link when
    both endpoints are shown."""
    result = dict(snapshot)
    shown_tables: dict[str, set[int]] = {}
    for section, (table, label, attribute) in RECORD_SECTIONS.items():
        value = snapshot.get(section)
        if not isinstance(value, dict):
            continue
        allowed = None if readable is None else readable.get(table, set())
        result[section] = _shown_section(value, label, attribute, allowed)
        shown_tables.setdefault(table, set()).update(_record_ids(result[section]))

    def keep(key: str, predicate) -> None:
        value = snapshot.get(key)
        if not isinstance(value, dict):
            return
        allowed = None if readable is None else readable.get(key, set())
        result[key] = {
            **value,
            "records": [
                record
                for record in value.get("records") or []
                if isinstance(record, dict)
                and (allowed is None or record.get("id") in allowed)
                and predicate(record)
            ],
        }

    def endpoint_shown(link_type, record_id) -> bool:
        table = _link_endpoint_table(link_type)
        return table is not None and record_id in shown_tables.get(table, set())

    keep("project_variables", lambda record: True)
    keep(
        "document_sections",
        lambda record: record.get("document_id") in shown_tables.get("documents", set()),
    )
    keep(
        "requirement_links",
        lambda record: record.get("source_id") in shown_tables.get("requirements", set())
        and record.get("target_id") in shown_tables.get("requirements", set()),
    )
    keep(
        "artefact_links",
        lambda record: endpoint_shown(record.get("source_type"), record.get("source_id"))
        and endpoint_shown(record.get("target_type"), record.get("target_id")),
    )
    return result


def _versioned(item: Baseline) -> bool:
    """Whether the baseline holds a snapshot with a schema version."""
    return isinstance(item.snapshot, dict) and "schema_version" in item.snapshot


async def _reader_scope(
    db: AsyncSession, user: User, project_id: int | None, items: list[Baseline]
) -> tuple[frozenset[str] | None, dict | None]:
    """The document types the user fully sees, for snapshots without a schema version, and
    the ids of the project's rows the user may read now, for versioned snapshots; each
    looked up at most once, and only when one of the baselines holds such a snapshot. Both
    are None for an administrator, an external user or a request without a project."""
    if user.role == UserRole.admin or user.role == UserRole.external or project_id is None:
        return None, None
    types = None
    readable: dict = {}
    if any(item.snapshot is not None and not _versioned(item) for item in items):
        types = await fully_visible_types(db, user, project_id)
    if any(_versioned(item) for item in items):
        readable = await _readable_ids(db, user, project_id)
    return types, readable


def _inventory(snapshot: dict) -> dict:
    """The snapshot without records: each category with its count and ids or titles, and
    no related record keys."""
    return {
        key: (
            {name: entry for name, entry in value.items() if name != "records"}
            if key in RECORD_SECTIONS and isinstance(value, dict)
            else value
        )
        for key, value in snapshot.items()
        if key not in RELATED_KEYS
    }


def _baseline_response(
    item: Baseline,
    current_user: User,
    types: frozenset[str] | None,
    readable: dict | None,
    *,
    records: bool,
) -> BaselineResponse:
    """The baseline as the user sees it. An external user gets no snapshot. A snapshot
    without a schema version keeps the sections whose document types are all in ``types``,
    the types of which the user sees every row. A versioned snapshot keeps every category
    with its captured count and, for an administrator, every captured record; for anyone
    else only the captured records whose ids are in ``readable``. With ``records`` False
    the snapshot carries the inventory only."""
    response = BaselineResponse.model_validate(item)
    if current_user.role == UserRole.external:
        response.snapshot = None
        return response
    snapshot = response.snapshot
    if snapshot is None:
        return response
    if "schema_version" in snapshot:
        allowed = None if current_user.role == UserRole.admin else readable or {}
        snapshot = _filter_records(snapshot, allowed)
        response.snapshot = snapshot if records else _inventory(snapshot)
        return response
    if types is not None:
        snapshot = {
            section: value
            for section, value in snapshot.items()
            if all(type_visible(types, code) for code in SNAPSHOT_SECTION_TYPES.get(section, ()))
        }
    response.snapshot = snapshot
    return response


async def _single_response(
    db: AsyncSession, item: Baseline, current_user: User, *, records: bool
) -> BaselineResponse:
    """The response for one baseline, with the user's scope on its project looked up once."""
    types, readable = await _reader_scope(db, current_user, item.project_id, [item])
    return _baseline_response(item, current_user, types, readable, records=records)


@router.get(
    "", response_model=list[BaselineResponse], responses={400: {"description": "Bad Request"}}
)
async def list_baselines(
    project_id: int | None = Query(None, description="Optional project filter"),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    if project_id is not None:
        await require_project_access(db, current_user, project_id, permission=("view", "baseline"))
    query = select(Baseline).order_by(Baseline.created_at.desc())
    if project_id:
        query = query.where(Baseline.project_id == project_id)
    elif current_user.role != UserRole.admin:
        raise HTTPException(status_code=400, detail="project_id is required for non-admin users")
    items = list((await db.execute(query)).scalars().all())
    types, readable = await _reader_scope(db, current_user, project_id, items)
    return [
        _baseline_response(item, current_user, types, readable, records=False) for item in items
    ]


@router.post("", response_model=BaselineResponse, status_code=201)
async def create_baseline(
    data: BaselineCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    project = await get_row_or_404(db, Project, data.project_id, "Project not found")

    await require_project_access(
        db,
        current_user,
        data.project_id,
        permission=("create", "baseline"),
    )

    baseline_id = await next_doc_id(
        db, Baseline, Baseline.baseline_id, data.project_id, project.prefix, "BL"
    )
    item = Baseline(
        project_id=data.project_id,
        baseline_id=baseline_id,
        name=data.name,
        description=data.description,
        baseline_type=data.baseline_type,
        snapshot=await _build_snapshot(db, data.project_id),
    )
    db.add(item)
    await db.flush()
    await record_audit_event(
        db,
        "baseline.created",
        target_type="baseline",
        target_id=item.baseline_id,
        project_id=item.project_id,
    )
    await db.refresh(item)
    return await _single_response(db, item, current_user, records=True)


@router.get(
    "/{baseline_id}", response_model=BaselineResponse, responses={404: {"description": "Not Found"}}
)
async def get_baseline(
    baseline_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    item = (
        await db.execute(select(Baseline).where(Baseline.id == baseline_id))
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=BASELINE_NOT_FOUND)
    await require_project_access(db, current_user, item.project_id, permission=("view", "baseline"))
    return await _single_response(db, item, current_user, records=True)


@router.patch("/{baseline_id}", response_model=BaselineResponse)
async def update_baseline(
    baseline_id: int,
    data: BaselineUpdate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    item = await get_visible_row(
        db,
        Baseline,
        baseline_id,
        BASELINE_NOT_FOUND,
        current_user,
        permission=("edit", "baseline"),
    )
    await apply_update(db, item, data, "baseline")
    return await _single_response(db, item, current_user, records=True)


@router.delete("/{baseline_id}", status_code=204)
async def delete_baseline(
    baseline_id: int,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    await delete_project_row(
        db,
        current_user,
        Baseline,
        baseline_id,
        BASELINE_NOT_FOUND,
        resource="baseline",
        audit_type="baseline",
    )
