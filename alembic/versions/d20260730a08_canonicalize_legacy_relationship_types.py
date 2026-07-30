"""canonicalize legacy relationship document types

Revision ID: d20260730a08
Revises: d20260729a07
Create Date: 2026-07-30

Existing relationship rows can still use the retired ``TCO`` and ``PROT``
identifiers. Canonicalize all stored identifiers so existing documents use the
same relationship rules and queries as newly created documents.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d20260730a08"
down_revision: Union[str, Sequence[str], None] = "d20260729a07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NORMALIZED_SOURCE = (
    "CASE UPPER(source_type) "
    "WHEN 'TCO' THEN 'CPT' "
    "WHEN 'PROT' THEN 'PRT' "
    "ELSE UPPER(source_type) END"
)
_NORMALIZED_TARGET = (
    "CASE UPPER(target_type) "
    "WHEN 'TCO' THEN 'CPT' "
    "WHEN 'PROT' THEN 'PRT' "
    "ELSE UPPER(target_type) END"
)


def upgrade() -> None:
    # Remove only semantic duplicates that would collide with the existing
    # unique constraint after canonicalization. Prefer an already-canonical
    # row, then retain the oldest remaining row.
    op.execute(
        sa.text(
            f"""
            DELETE FROM artefact_links
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY
                                {_NORMALIZED_SOURCE},
                                source_id,
                                {_NORMALIZED_TARGET},
                                target_id,
                                role
                            ORDER BY
                                CASE
                                    WHEN source_type = {_NORMALIZED_SOURCE}
                                     AND target_type = {_NORMALIZED_TARGET}
                                    THEN 0
                                    ELSE 1
                                END,
                                id
                        ) AS duplicate_rank
                    FROM artefact_links
                ) AS normalized_links
                WHERE duplicate_rank > 1
            )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE artefact_links
            SET
                source_type = {_NORMALIZED_SOURCE},
                target_type = {_NORMALIZED_TARGET}
            WHERE
                source_type <> {_NORMALIZED_SOURCE}
                OR target_type <> {_NORMALIZED_TARGET}
            """
        )
    )


def downgrade() -> None:
    # Canonical rows do not retain enough information to distinguish links
    # originally stored under a legacy identifier.
    pass
