"""artefact creator

Adds a nullable created_by_id (users.id) to the ten artefact tables. Existing rows keep
NULL. Downgrade drops the column.

Revision ID: a4c1d2e3f405
Revises: 449b8eddaf9e
Create Date: 2026-10-01

"""

import sqlalchemy as sa

from alembic import op

revision = "a4c1d2e3f405"
down_revision = "449b8eddaf9e"
branch_labels = None
depends_on = None

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
    """Add created_by_id to each artefact table."""
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        )


def downgrade() -> None:
    """Drop created_by_id from each artefact table."""
    for table in TABLES:
        op.drop_column(table, "created_by_id")
