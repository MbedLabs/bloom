"""audit_events: indexes on outcome and ip

Revision ID: 0ef8b87db4d3
Revises: 637f976e78e0
Create Date: 2026-10-28

Adds the indexes that the denied-request count per address and the outcome and address
filters of the audit log read.
"""

from alembic import op

revision = "0ef8b87db4d3"
down_revision = "637f976e78e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the outcome and ip indexes of audit_events."""
    op.create_index("ix_audit_events_outcome", "audit_events", ["outcome"])
    op.create_index("ix_audit_events_ip", "audit_events", ["ip"])


def downgrade() -> None:
    """Drop the outcome and ip indexes of audit_events."""
    op.drop_index("ix_audit_events_ip", table_name="audit_events")
    op.drop_index("ix_audit_events_outcome", table_name="audit_events")
