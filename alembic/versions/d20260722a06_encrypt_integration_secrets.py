"""encrypt integration credentials at rest

Revision ID: d20260722a06
Revises: d20260722a05
Create Date: 2026-07-23

GitHub/GitLab access tokens and webhook secrets are now stored Fernet-encrypted
in a ``fernet:v1:`` envelope. Widen ``webhook_secret`` to TEXT (an envelope can
exceed 255 chars) and clear any pre-existing plaintext credentials so no
plaintext remains at rest — administrators re-enter (rotate) them, after which
they are stored encrypted. Values already in the envelope format are untouched.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d20260722a06"
down_revision: Union[str, Sequence[str], None] = "d20260722a05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "integration_settings",
        "webhook_secret",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )
    # Clear legacy plaintext credentials (anything not already enveloped).
    op.execute(
        sa.text(
            "UPDATE integration_settings SET token_encrypted = NULL "
            "WHERE token_encrypted IS NOT NULL AND token_encrypted NOT LIKE 'fernet:v1:%'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE integration_settings SET webhook_secret = NULL "
            "WHERE webhook_secret IS NOT NULL AND webhook_secret NOT LIKE 'fernet:v1:%'"
        )
    )


def downgrade() -> None:
    op.alter_column(
        "integration_settings",
        "webhook_secret",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
