"""add the external value to the userrole enum"""

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
