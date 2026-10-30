"""integration_settings: scheduled sync state; defects: whether the linked issue is closed

Revision ID: b7d3e91f4a26
Revises: 9e4a2c7d18b0
Create Date: 2026-10-26

"""

import sqlalchemy as sa

from alembic import op

revision = "b7d3e91f4a26"
down_revision = "9e4a2c7d18b0"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("sync_checked_at", sa.DateTime(), True, None),
    ("synced_at", sa.DateTime(), True, None),
    ("sync_error", sa.Text(), True, None),
    ("sync_warning", sa.Text(), True, None),
    ("sync_created", sa.Integer(), False, sa.text("0")),
    ("sync_updated", sa.Integer(), False, sa.text("0")),
    ("sync_full_scan", sa.Boolean(), False, sa.true()),
    ("sync_scan_from", sa.DateTime(), True, None),
    ("sync_removal_cursor", sa.Integer(), False, sa.text("0")),
)


def upgrade() -> None:
    """Add the scheduled sync columns, whose existing rows get the defaults, and the
    defects' closed flag, set from the recorded GitHub or GitLab issue state."""
    for name, kind, nullable, default in _COLUMNS:
        op.add_column(
            "integration_settings",
            sa.Column(name, kind, nullable=nullable, server_default=default),
        )
    op.add_column("defects", sa.Column("external_issue_closed", sa.Boolean(), nullable=True))
    op.execute(
        "UPDATE defects SET external_issue_closed = (external_issue_state = 'closed') "
        "WHERE external_tracker IN ('github', 'gitlab') AND external_issue_state IS NOT NULL"
    )


def downgrade() -> None:
    """Drop the defects' closed flag and the scheduled sync columns."""
    op.drop_column("defects", "external_issue_closed")
    for name, *_ in reversed(_COLUMNS):
        op.drop_column("integration_settings", name)
