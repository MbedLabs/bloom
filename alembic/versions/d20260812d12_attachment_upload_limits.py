"""rate and concurrency controls for interactive attachment uploads

Revision ID: d20260812d12
Revises: d20260810c11
Create Date: 2026-08-12
"""

import sqlalchemy as sa

from alembic import op

revision = "d20260812d12"
down_revision = "d20260810c11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attachment_upload_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_attachment_upload_attempts_user_id",
        "attachment_upload_attempts",
        ["user_id"],
    )
    op.create_index(
        "ix_attachment_upload_attempts_created_at",
        "attachment_upload_attempts",
        ["created_at"],
    )

    op.create_table(
        "attachment_upload_leases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_attachment_upload_leases_user_id",
        "attachment_upload_leases",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        "ix_attachment_upload_leases_expires_at",
        "attachment_upload_leases",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_attachment_upload_leases_expires_at", table_name="attachment_upload_leases")
    op.drop_index("ix_attachment_upload_leases_user_id", table_name="attachment_upload_leases")
    op.drop_table("attachment_upload_leases")
    op.drop_index(
        "ix_attachment_upload_attempts_created_at", table_name="attachment_upload_attempts"
    )
    op.drop_index("ix_attachment_upload_attempts_user_id", table_name="attachment_upload_attempts")
    op.drop_table("attachment_upload_attempts")
