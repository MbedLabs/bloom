"""Jira outbound sync: the send start marker, the sync direction and rate, and send claims

Revision ID: c4e8a2f6b1d3
Revises: b2d4f6a8c0e1
Create Date: 2026-11-04

Creates the system_markers table and records, as defects_to_jira_since, the moment this
migration runs: defects created from then on are the ones the Jira sync sends. Replaces
integration_settings.two_way with direction (both for a two-way setting, jira_to_bloom
otherwise), adds integration_settings.auto_sync_minutes at 10 and defects.jira_send_started_at.
"""

from datetime import datetime, timezone

import sqlalchemy as sa

from alembic import op

revision = "c4e8a2f6b1d3"
down_revision = "b2d4f6a8c0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the marker table, move two_way to direction, add the rate and the claim."""
    markers = op.create_table(
        "system_markers",
        sa.Column("name", sa.String(length=64), primary_key=True),
        sa.Column("marked_at", sa.DateTime(), nullable=False),
    )
    op.bulk_insert(
        markers,
        [
            {
                "name": "defects_to_jira_since",
                "marked_at": datetime.now(timezone.utc).replace(tzinfo=None),
            }
        ],
    )
    with op.batch_alter_table("integration_settings") as batch:
        batch.add_column(
            sa.Column(
                "direction",
                sa.String(length=20),
                nullable=False,
                server_default="jira_to_bloom",
            )
        )
        batch.add_column(
            sa.Column("auto_sync_minutes", sa.Integer(), nullable=False, server_default="10")
        )
    op.execute(sa.text("UPDATE integration_settings SET direction = 'both' WHERE two_way = true"))
    with op.batch_alter_table("integration_settings") as batch:
        batch.drop_column("two_way")
    with op.batch_alter_table("defects") as batch:
        batch.add_column(sa.Column("jira_send_started_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Drop the claim and the rate, move direction back to two_way, drop the marker table."""
    with op.batch_alter_table("defects") as batch:
        batch.drop_column("jira_send_started_at")
    with op.batch_alter_table("integration_settings") as batch:
        batch.add_column(
            sa.Column("two_way", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    op.execute(
        sa.text("UPDATE integration_settings SET two_way = true WHERE direction <> 'jira_to_bloom'")
    )
    with op.batch_alter_table("integration_settings") as batch:
        batch.drop_column("auto_sync_minutes")
        batch.drop_column("direction")
    op.drop_table("system_markers")
