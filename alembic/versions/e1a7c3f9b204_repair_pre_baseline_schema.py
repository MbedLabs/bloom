"""repair databases created before the locked baseline

Adds integration_settings.account_email and the change_request_sync_events table
where they are missing. Databases built from the baseline already have both, so
the statements change nothing there.

Revision ID: e1a7c3f9b204
Revises: d8f3b2c6a910
Create Date: 2026-09-25

"""

from alembic import op

revision = "e1a7c3f9b204"
down_revision = "d8f3b2c6a910"
branch_labels = None
depends_on = None

REPAIR_STATEMENTS = (
    "ALTER TABLE integration_settings ADD COLUMN IF NOT EXISTS account_email VARCHAR(255)",
    """
    CREATE TABLE IF NOT EXISTS change_request_sync_events (
        id SERIAL PRIMARY KEY,
        change_request_id INTEGER NOT NULL REFERENCES change_requests (id),
        direction VARCHAR(10) NOT NULL,
        tracker VARCHAR(20) NOT NULL,
        event_type VARCHAR(50) NOT NULL,
        payload_summary TEXT,
        success BOOLEAN NOT NULL,
        error_message TEXT,
        external_event_id VARCHAR(255),
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_change_request_sync_events_change_request_id "
    "ON change_request_sync_events (change_request_id)",
)


def upgrade() -> None:
    """Create the column and the table the baseline defines, where they are missing."""
    for statement in REPAIR_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    """Keep the column and the table: the baseline defines them, so they stay."""
