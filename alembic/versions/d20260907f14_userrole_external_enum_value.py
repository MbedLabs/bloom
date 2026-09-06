"""add the external value to the userrole enum

Revision ID: d20260907f14
Revises: d20260906e13
Create Date: 2026-09-07

The reviewer role was renamed to external in the application, but the
PostgreSQL enum backing users.role was never changed. Databases created from
the locked baseline get the new labels and work; every database created before
the rename still has ('admin', 'maintainer', 'reviewer'), so writing the new
value fails at the driver:

    asyncpg.exceptions.InvalidTextRepresentationError:
      invalid input value for enum userrole: "external"

Changing a user to external therefore returned 500 on any pre-existing
deployment, which is exactly what a live instance was doing.

The enum is rebuilt rather than extended with ALTER TYPE ... ADD VALUE, because
that form cannot be used in the same transaction that writes the new label, and
any surviving reviewer rows have to be moved over in the same step. Swapping
through text keeps the whole change inside the migration's transaction.

Idempotent: if external is already present the revision does nothing, so a
database built from the baseline is unaffected.
"""

from alembic import op

revision = "d20260907f14"
down_revision = "d20260906e13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'userrole' AND e.enumlabel = 'external'
            ) THEN
                ALTER TABLE users ALTER COLUMN role DROP DEFAULT;
                ALTER TABLE users ALTER COLUMN role TYPE text USING role::text;
                UPDATE users SET role = 'external' WHERE role = 'reviewer';
                DROP TYPE userrole;
                CREATE TYPE userrole AS ENUM ('admin', 'maintainer', 'external');
                ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole;
                ALTER TABLE users ALTER COLUMN role SET DEFAULT 'external'::userrole;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # Mirror image: external becomes reviewer again. A deployment that has
    # already created external users keeps them, renamed.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'userrole' AND e.enumlabel = 'reviewer'
            ) THEN
                ALTER TABLE users ALTER COLUMN role DROP DEFAULT;
                ALTER TABLE users ALTER COLUMN role TYPE text USING role::text;
                UPDATE users SET role = 'reviewer' WHERE role = 'external';
                DROP TYPE userrole;
                CREATE TYPE userrole AS ENUM ('admin', 'maintainer', 'reviewer');
                ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole;
                ALTER TABLE users ALTER COLUMN role SET DEFAULT 'reviewer'::userrole;
            END IF;
        END
        $$;
        """
    )
