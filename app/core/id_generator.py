"""
Safe ID generation using MAX(numeric_suffix)+1 instead of COUNT()+1.
Handles gaps from deletions correctly.
"""

import re

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

ALLOWED_TYPE_CODES = frozenset(
    {
        "REQ",
        "TC",
        "DES",
        "RSK",
        "CHG",
        "CPT",
        "DEF",
        "SPEC",
        "PRT",
        "RPT",
        "STD",
        "BL",
        "TS",
        "CMP",
    }
)

PROJECT_PREFIX_PATTERN = re.compile(r"^[A-Z]{3}$")
# Three digits is the floor, not the ceiling: a project that passes 999 keeps
# counting and every id in that project and type widens to match, so
# FLT-REQ-001 becomes FLT-REQ-0001 the moment FLT-REQ-1000 is needed. Equal
# width is what keeps the ids sorting correctly as plain strings.
DOC_ID_PATTERN = re.compile(r"^([A-Z]{3})-([A-Z]+)-([0-9]{3,})$")
ID_MIN_WIDTH = 3


def _validate_naming_parts(prefix: str, type_code: str) -> None:
    if not PROJECT_PREFIX_PATTERN.fullmatch(prefix):
        raise ValueError("Project prefix must be exactly three uppercase letters.")
    if type_code not in ALLOWED_TYPE_CODES:
        raise ValueError(f"Unsupported document type code: {type_code}")


def normalize_doc_id(
    value: str,
    *,
    expected_type_code: str | None = None,
    expected_project_prefix: str | None = None,
) -> str:
    """Normalize and validate a creator-supplied ID like PRJ-REQ-001."""
    if not isinstance(value, str):
        raise ValueError("ID must follow PRJ-TYP-001.")

    normalized = value.strip().upper()
    match = DOC_ID_PATTERN.fullmatch(normalized)
    if not match:
        raise ValueError("ID must follow PRJ-TYP-001: three letters, allowed type, three digits.")

    project_prefix, type_code, _suffix = match.groups()
    _validate_naming_parts(project_prefix, type_code)

    if expected_type_code is not None and type_code != expected_type_code:
        raise ValueError(f"ID type must be {expected_type_code}.")
    if expected_project_prefix is not None and project_prefix != expected_project_prefix:
        raise ValueError(f"ID project prefix must be {expected_project_prefix}.")

    return normalized


def id_width(number: int) -> int:
    """Digits an id suffix needs: never fewer than three, more once required."""
    return max(ID_MIN_WIDTH, len(str(number)))


def format_doc_id(prefix: str, type_code: str, number: int, width: int | None = None) -> str:
    """Render one id, padded to ``width`` or to the width ``number`` requires."""
    return f"{prefix}-{type_code}-{number:0{width or id_width(number)}d}"


def widened_ids(existing_ids: list[str], prefix: str, type_code: str, width: int) -> dict[str, str]:
    """Map old id to new for every id narrower than ``width``.

    Returned rather than applied so the caller owns the write, and so the rule
    can be tested without a database. Ids already at the width, and anything
    that does not parse, are left out.
    """
    search_prefix = f"{prefix}-{type_code}-"
    renames: dict[str, str] = {}
    for item_id in existing_ids:
        if not item_id.startswith(search_prefix):
            continue
        suffix = item_id[len(search_prefix) :]
        if not suffix.isdigit() or len(suffix) >= width:
            continue
        renames[item_id] = format_doc_id(prefix, type_code, int(suffix), width)
    return renames


def compute_next_id(existing_ids: list[str], prefix: str, type_code: str) -> str:
    """
    Pure function: given a list of existing ID strings, compute the next one.
    Uses MAX(numeric_suffix)+1 to be safe after deletions.
    """
    _validate_naming_parts(prefix, type_code)

    search_prefix = f"{prefix}-{type_code}-"
    prefix_len = len(search_prefix)
    max_num = 0
    for item_id in existing_ids:
        if not item_id.startswith(search_prefix):
            continue

        suffix = item_id[prefix_len:]
        if not suffix.isdigit():
            continue

        try:
            num = int(suffix)
            if num > max_num:
                max_num = num
        except (ValueError, IndexError):
            continue

    next_num = max_num + 1
    return format_doc_id(prefix, type_code, next_num)


async def next_doc_id(
    db: AsyncSession,
    model,
    id_column,
    project_id: int,
    prefix: str,
    type_code: str,
) -> str:
    """
    Generate the next human-readable ID for a doc type.

    Args:
        model: SQLAlchemy model class (e.g. Requirement)
        id_column: The column holding the string ID (e.g. Requirement.req_id)
        project_id: Target project ID
        prefix: Project prefix (e.g. "PRJ")
        type_code: Type code (e.g. "REQ", "TC", "DES")

    Returns:
        Next ID string like "PRJ-REQ-004"
    """
    search_prefix = f"{prefix}-{type_code}-"
    rows = (
        (
            await db.execute(
                select(id_column).where(
                    model.project_id == project_id,
                    id_column.like(f"{search_prefix}%"),
                )
            )
        )
        .scalars()
        .all()
    )

    next_id = compute_next_id(rows, prefix, type_code)
    width = len(next_id.rsplit("-", 1)[1])

    # Crossing a power of ten widens every id in this project and type, so
    # FLT-REQ-001 becomes FLT-REQ-0001 alongside the new FLT-REQ-1000. Without
    # it the two widths coexist and the ids stop sorting as strings.
    #
    # One statement per id, but this runs once in the life of a project and type
    # - only on the single creation that crosses the boundary - and the ids are
    # rewritten in place, so a rename never collides with a row it has not
    # reached yet.
    for old_id, new_id in widened_ids(rows, prefix, type_code, width).items():
        await db.execute(
            update(model)
            .where(model.project_id == project_id, id_column == old_id)
            .values({id_column.key: new_id})
        )

    return next_id
