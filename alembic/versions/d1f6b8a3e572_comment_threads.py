"""artefact_comments: threads, anchored passages and resolution

Revision ID: d1f6b8a3e572
Revises: c4a8e2f71d93
Create Date: 2026-10-27

"""

import sqlalchemy as sa

from alembic import op

revision = "d1f6b8a3e572"
down_revision = "c4a8e2f71d93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the thread parent, the quoted passage and the resolution columns."""
    op.add_column(
        "artefact_comments",
        sa.Column(
            "parent_id",
            sa.Integer(),
            sa.ForeignKey("artefact_comments.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_artefact_comments_parent_id", "artefact_comments", ["parent_id"])
    op.add_column("artefact_comments", sa.Column("anchor_exact", sa.Text(), nullable=True))
    op.add_column(
        "artefact_comments", sa.Column("anchor_prefix", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "artefact_comments", sa.Column("anchor_suffix", sa.String(length=64), nullable=True)
    )
    op.add_column("artefact_comments", sa.Column("resolved_at", sa.DateTime(), nullable=True))
    op.add_column(
        "artefact_comments",
        sa.Column(
            "resolved_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Drop the thread, passage and resolution columns."""
    op.drop_column("artefact_comments", "resolved_by_id")
    op.drop_column("artefact_comments", "resolved_at")
    op.drop_column("artefact_comments", "anchor_suffix")
    op.drop_column("artefact_comments", "anchor_prefix")
    op.drop_column("artefact_comments", "anchor_exact")
    op.drop_index("ix_artefact_comments_parent_id", table_name="artefact_comments")
    op.drop_column("artefact_comments", "parent_id")
