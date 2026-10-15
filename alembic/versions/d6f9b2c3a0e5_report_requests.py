"""Durable report-request workflow."""

import sqlalchemy as sa

from alembic import op

revision = "d6f9b2c3a0e5"
down_revision = "c5e8a1f2b9d4"
branch_labels = None
depends_on = None


def upgrade():
    """Add report-request storage without changing existing evidence or identities."""
    op.create_table(
        "report_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("bud_run_id", sa.Integer(), nullable=False),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("publisher", sa.String(300), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_report_requests_project_id", "report_requests", ["project_id"])
    op.create_index(
        "uq_report_requests_pending",
        "report_requests",
        ["project_id", "bud_run_id", "requester_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )


def downgrade():
    """Remove empty request storage; retain populated workflow history."""
    if op.get_bind().execute(sa.text("SELECT 1 FROM report_requests LIMIT 1")).first():
        raise RuntimeError("Report requests exist; preserve them before downgrading")
    op.drop_table("report_requests")
