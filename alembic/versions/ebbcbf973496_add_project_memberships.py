"""add_project_memberships

Revision ID: ebbcbf973496
Revises:
Create Date: 2026-05-18 09:51:26.002452

Project-scoped role assignments:
- project_memberships: per-user per-project role (maintainer/external).
  Admins skip this table — their global User.role suffices.
- project_external_doc_types: doc-type visibility whitelist for external
  users. Empty rows set → external user sees nothing (deny-by-default).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ebbcbf973496"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Base schema is managed by SQLAlchemy create_tables() (models are source of truth).
    # This migration exists to anchor the revision chain.
    pass


def downgrade() -> None:
    pass

