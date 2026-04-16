"""
Safe ID generation using MAX(numeric_suffix)+1 instead of COUNT()+1.
Handles gaps from deletions correctly.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def compute_next_id(existing_ids: list[str], prefix: str, type_code: str) -> str:
    """
    Pure function: given a list of existing ID strings, compute the next one.
    Uses MAX(numeric_suffix)+1 to be safe after deletions.
    """
    search_prefix = f"{prefix}-{type_code}-"
    prefix_len = len(search_prefix)
    max_num = 0
    for item_id in existing_ids:
        try:
            num = int(item_id[prefix_len:])
            if num > max_num:
                max_num = num
        except (ValueError, IndexError):
            continue
    return f"{search_prefix}{max_num + 1:03d}"


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
