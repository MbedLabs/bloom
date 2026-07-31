"""jira integration and change request external links

Revision ID: d20260731a09
Revises: d20260730a08
Create Date: 2026-07-31

Adds the storage Jira needs and extends external tracker linkage to change
requests:

* ``integration_settings.account_email`` — Jira Cloud authenticates with
  ``email:api_token`` Basic auth, so the account owning the token is recorded
  next to it. GitHub and GitLab leave it NULL.
* ``change_requests.external_*`` — mirrors the columns already on ``defects`` so
  a change request can track an issue in GitHub, GitLab, or Jira.
* ``change_request_sync_events`` — the change-request counterpart of
  ``defect_sync_events``.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d20260731a09"
down_revision: Union[str, Sequence[str], None] = "d20260730a08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CHANGE_REQUEST_COLUMNS = (
    ("external_tracker", sa.String(length=20)),
    ("external_repo_full_name", sa.String(length=255)),
    ("external_issue_number", sa.Integer()),
    ("external_issue_url", sa.String(length=500)),
    ("external_issue_state", sa.String(length=30)),
    ("external_last_event_at", sa.DateTime()),
)


def upgrade() -> None:
    # The base revision builds the schema with Base.metadata.create_all(), so on a
    # fresh install every object below already exists. Each step is therefore
    # guarded, and only an established database actually gets altered.
    bind = op.get_bind()

    integration_columns = {c["name"] for c in sa.inspect(bind).get_columns("integration_settings")}
    if "account_email" not in integration_columns:
        op.add_column(
            "integration_settings",
            sa.Column("account_email", sa.String(length=255), nullable=True),
        )

    change_columns = {c["name"] for c in sa.inspect(bind).get_columns("change_requests")}
    for name, column_type in _CHANGE_REQUEST_COLUMNS:
        if name not in change_columns:
            op.add_column("change_requests", sa.Column(name, column_type, nullable=True))

    change_indexes = {i["name"] for i in sa.inspect(bind).get_indexes("change_requests")}
    if "ix_change_requests_external_issue" not in change_indexes:
        # Inbound webhooks look a change request up by (tracker, repo, issue number).
        op.create_index(
            "ix_change_requests_external_issue",
            "change_requests",
            ["external_tracker", "external_repo_full_name", "external_issue_number"],
        )

    if "change_request_sync_events" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "change_request_sync_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("change_request_id", sa.Integer(), nullable=False),
            sa.Column("direction", sa.String(length=10), nullable=False),
            sa.Column("tracker", sa.String(length=20), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("payload_summary", sa.Text(), nullable=True),
            sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("external_event_id", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["change_request_id"], ["change_requests.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    sync_indexes = {i["name"] for i in sa.inspect(bind).get_indexes("change_request_sync_events")}
    if "ix_change_request_sync_events_change_request_id" not in sync_indexes:
        op.create_index(
            "ix_change_request_sync_events_change_request_id",
            "change_request_sync_events",
            ["change_request_id"],
        )


def downgrade() -> None:
    op.drop_index(
        "ix_change_request_sync_events_change_request_id",
        table_name="change_request_sync_events",
    )
    op.drop_table("change_request_sync_events")

    op.drop_index("ix_change_requests_external_issue", table_name="change_requests")
    op.drop_column("change_requests", "external_last_event_at")
    op.drop_column("change_requests", "external_issue_state")
    op.drop_column("change_requests", "external_issue_url")
    op.drop_column("change_requests", "external_issue_number")
    op.drop_column("change_requests", "external_repo_full_name")
    op.drop_column("change_requests", "external_tracker")

    op.drop_column("integration_settings", "account_email")
