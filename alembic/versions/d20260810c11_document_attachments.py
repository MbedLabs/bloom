"""files held against a document

Revision ID: d20260810c11
Revises: d20260805b10
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op

revision = "d20260810c11"
down_revision = "d20260805b10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.String(length=200), nullable=True),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_attachments_document_id", "document_attachments", ["document_id"]
    )
    op.create_index("ix_document_attachments_source_ref", "document_attachments", ["source_ref"])
    op.create_index("ix_document_attachments_created_at", "document_attachments", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_document_attachments_created_at", table_name="document_attachments")
    op.drop_index("ix_document_attachments_source_ref", table_name="document_attachments")
    op.drop_index("ix_document_attachments_document_id", table_name="document_attachments")
    op.drop_table("document_attachments")
