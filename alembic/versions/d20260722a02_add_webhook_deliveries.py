"""add webhook deliveries

Revision ID: d20260722a02
Revises: d20260722a01
Create Date: 2026-07-22
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d20260722a02"
down_revision: Union[str, Sequence[str], None] = "d20260722a01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "webhook_deliveries" in inspector.get_table_names():
        return
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("integration_setting_id", sa.Integer(), nullable=False),
        sa.Column("tracker", sa.String(length=20), nullable=False),
        sa.Column("delivery_id", sa.String(length=255), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["integration_setting_id"], ["integration_settings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tracker", "delivery_id", name="uq_webhook_tracker_delivery"
        ),
    )
    op.create_index(
        "ix_webhook_deliveries_integration_setting_id",
        "webhook_deliveries",
        ["integration_setting_id"],
    )
    op.create_index(
        "ix_webhook_deliveries_received_at",
        "webhook_deliveries",
        ["received_at"],
    )


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
