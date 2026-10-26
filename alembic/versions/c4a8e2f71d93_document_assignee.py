"""artefact_workflows: the document's assignee

Revision ID: c4a8e2f71d93
Revises: b7d3e91f4a26
Create Date: 2026-10-27

"""

import sqlalchemy as sa

from alembic import op

revision = "c4a8e2f71d93"
down_revision = "b7d3e91f4a26"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the assignee, set to each workflow's current revision creator."""
    op.add_column(
        "artefact_workflows",
        sa.Column(
            "assignee_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.execute("UPDATE artefact_workflows SET assignee_id = revision_creator_id")


def downgrade() -> None:
    """Drop the assignee."""
    op.drop_column("artefact_workflows", "assignee_id")
