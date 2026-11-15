"""requirements: drop parent_id

Revision ID: a7d2c5f81b39
Revises: c4e8a2f6b1d3
Create Date: 2026-11-10

Requirements form no tree: they relate only through links. Drops requirements.parent_id with
its index and foreign key; the values it held are not kept.
"""

import sqlalchemy as sa

from alembic import op

revision = "a7d2c5f81b39"
down_revision = "c4e8a2f6b1d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Drop the parent column, its index and its foreign key."""
    op.drop_index("ix_requirements_parent_id", table_name="requirements")
    with op.batch_alter_table("requirements") as batch:
        batch.drop_column("parent_id")


def downgrade() -> None:
    """Add back an empty parent column with its index and foreign key."""
    with op.batch_alter_table("requirements") as batch:
        batch.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "requirements_parent_id_fkey", "requirements", ["parent_id"], ["id"]
        )
    op.create_index("ix_requirements_parent_id", "requirements", ["parent_id"], unique=False)
