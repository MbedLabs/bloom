"""add artefact visibility columns

Revision ID: f1c2d3e4b5a6
Revises: 70a4c05b2693
Create Date: 2026-06-10 15:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1c2d3e4b5a6"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = (
    "requirements",
    "test_cases",
    "documents",
    "test_suites",
    "test_campaigns",
    "design_items",
    "risk_items",
    "change_requests",
    "test_concepts",
    "defects",
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table in TABLES:
        columns = [c["name"] for c in inspector.get_columns(table)]
        if "visibility" not in columns:
            op.add_column(
                table,
                sa.Column(
                    "visibility",
                    sa.String(length=20),
                    nullable=False,
                    server_default="internal",
                ),
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table in reversed(TABLES):
        columns = [c["name"] for c in inspector.get_columns(table)]
        if "visibility" in columns:
            op.drop_column(table, "visibility")
