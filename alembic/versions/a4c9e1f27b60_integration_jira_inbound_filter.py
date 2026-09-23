"""integration_settings: Jira inbound filter, priority map and two-way switch

Revision ID: a4c9e1f27b60
Revises: 7dbc5eb75da5
Create Date: 2026-09-24

"""

import sqlalchemy as sa

from alembic import op

revision = "a4c9e1f27b60"
down_revision = "7dbc5eb75da5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the Jira issue filter, the priority map and the two-way switch (off)."""
    op.add_column("integration_settings", sa.Column("jira_issue_types", sa.JSON(), nullable=True))
    op.add_column(
        "integration_settings", sa.Column("jira_label", sa.String(length=255), nullable=True)
    )
    op.add_column("integration_settings", sa.Column("jira_jql", sa.Text(), nullable=True))
    op.add_column(
        "integration_settings",
        sa.Column("jira_reference_field", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "integration_settings", sa.Column("jira_priority_map", sa.JSON(), nullable=True)
    )
    op.add_column(
        "integration_settings",
        sa.Column("two_way", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Drop the Jira issue filter, the priority map and the two-way switch."""
    for column in (
        "two_way",
        "jira_priority_map",
        "jira_reference_field",
        "jira_jql",
        "jira_label",
        "jira_issue_types",
    ):
        op.drop_column("integration_settings", column)
