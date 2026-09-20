"""report_branding: instance company logo for PDF reports

Revision ID: f3c17b0a55de
Revises: e2f1a9c4d7b3
Create Date: 2026-09-20

"""

import sqlalchemy as sa

from alembic import op

revision = "f3c17b0a55de"
down_revision = "e2f1a9c4d7b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the report_branding table."""
    op.create_table(
        "report_branding",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("logo", sa.LargeBinary(), nullable=True),
        sa.Column("logo_content_type", sa.String(length=100), nullable=True),
        sa.Column("logo_filename", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop the report_branding table."""
    op.drop_table("report_branding")
