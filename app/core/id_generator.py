"""
Safe ID generation using MAX(numeric_suffix)+1 instead of COUNT()+1.
Handles gaps from deletions correctly.
"""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ALLOWED_TYPE_CODES = frozenset(
    {
        "REQ",
        "TC",
        "DES",
        "RSK",
        "CHG",
        "TCO",
        "SPEC",
        "PROT",
        "RPT",
        "STD",
        "BL",
        "TS",
    }
)

PROJECT_PREFIX_PATTERN = re.compile(r"^[A-Z]{3}$")
DOC_ID_PATTERN = re.compile(r"^([A-Z]{3})-([A-Z]+)-([0-9]{3})$")
ID_SUFFIX_LIMIT = 999


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
    if next_num > ID_SUFFIX_LIMIT:
        raise ValueError(f"ID sequence exhausted for {prefix}-{type_code}; maximum is 999")

    return f"{search_prefix}{next_num:03d}"


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

    return compute_next_id(rows, prefix, type_code)
