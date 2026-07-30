"""add administrator approval state to email changes

Revision ID: d20260729a07
Revises: d20260722a06
Create Date: 2026-07-29

User-requested email changes now wait for administrator approval before a
confirmation token is issued. Existing pending changes from revision
d20260722a05 already have confirmation tokens, so they are preserved as
``awaiting_confirmation`` during upgrade. Integrations left enabled without a
complete encrypted credential pair by revision d20260722a06 are disabled until
an administrator rotates the credentials and explicitly enables them again.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d20260729a07"
down_revision: Union[str, Sequence[str], None] = "d20260722a06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    user_columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "email_change_status" not in user_columns:
        op.add_column(
            "users",
            sa.Column("email_change_status", sa.String(length=32), nullable=True),
        )
    if "email_change_requested_at" not in user_columns:
        op.add_column(
            "users",
            sa.Column("email_change_requested_at", sa.DateTime(), nullable=True),
        )
    token_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("user_tokens")
    }
    if "target_email" not in token_columns:
        op.add_column(
            "user_tokens",
            sa.Column("target_email", sa.String(length=255), nullable=True),
        )
    op.execute(
        sa.text(
            "UPDATE user_tokens "
            "SET target_email = ("
            "SELECT users.pending_email FROM users "
            "WHERE users.id = user_tokens.user_id"
            ") "
            "WHERE purpose = 'email_change' "
            "AND used_at IS NULL "
            "AND target_email IS NULL "
            "AND EXISTS ("
            "SELECT 1 FROM users "
            "WHERE users.id = user_tokens.user_id "
            "AND users.pending_email IS NOT NULL"
            ")"
        )
    )
    op.execute(
        sa.text(
            "UPDATE integration_settings SET enabled = FALSE "
            "WHERE enabled = TRUE AND ("
            "token_encrypted IS NULL "
            "OR token_encrypted NOT LIKE 'fernet:v1:%' "
            "OR webhook_secret IS NULL "
            "OR webhook_secret NOT LIKE 'fernet:v1:%'"
            ")"
        )
    )
    op.execute(
        sa.text(
            "UPDATE users "
            "SET email_change_status = 'awaiting_confirmation', "
            "email_change_requested_at = CURRENT_TIMESTAMP "
            "WHERE pending_email IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("user_tokens", "target_email")
    op.drop_column("users", "email_change_requested_at")
    op.drop_column("users", "email_change_status")
