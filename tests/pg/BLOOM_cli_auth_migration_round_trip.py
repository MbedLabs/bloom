"""
* @file     ${tests/pg/BLOOM_cli_auth_migration_round_trip.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The CLI session migration keeps existing rows through upgrade, downgrade and upgrade.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests the migration on new PostgreSQL seeded at the older revision.
"""

from tests.pg.cli_auth_migration_round_trip import CliAuthMigrationRoundTripBase


class CliAuthMigrationRoundTripTest(CliAuthMigrationRoundTripBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.postgres:
            return
        self.commands = [
            self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_BEFORE_CLI)
        ]
        self.ids = self.bloom.bloom_seed_retained_rows()
        self.before_revision = self.bloom.bloom_read_revision()
        self.before_rows = self.bloom.bloom_read_retained_rows(self.ids)
        self.before_table = self.bloom.bloom_read_cli_session_table()

        self.commands.append(
            self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        )
        self.heads = self.bloom.bloom_list_alembic_heads()
        self.upgraded_revision = self.bloom.bloom_read_revision()
        self.upgraded_rows = self.bloom.bloom_read_retained_rows(self.ids)
        self.upgraded_table = self.bloom.bloom_read_cli_session_table()

        self.bloom.bloom_add_cli_sessions(self.ids["user"])
        self.stored_sessions = self.bloom.bloom_read_cli_session_table()["sessions"]

        self.commands.append(
            self.bloom.bloom_run_alembic("downgrade", self.parameters.MIGRATION_BEFORE_CLI)
        )
        self.downgraded_revision = self.bloom.bloom_read_revision()
        self.downgraded_rows = self.bloom.bloom_read_retained_rows(self.ids)
        self.downgraded_table = self.bloom.bloom_read_cli_session_table()

        self.commands.append(
            self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        )
        self.reupgraded_revision = self.bloom.bloom_read_revision()
        self.reupgraded_rows = self.bloom.bloom_read_retained_rows(self.ids)
        self.reupgraded_table = self.bloom.bloom_read_cli_session_table()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthMigrationRoundTripTest().run()
