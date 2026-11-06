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
        self.tc_postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.tc_postgres:
            return
        self.tc_commands = [
            self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_BEFORE_CLI)
        ]
        self.tc_ids = self.bloom.bloom_seed_retained_rows()
        self.tc_before_revision = self.bloom.bloom_read_revision()
        self.tc_before_rows = self.bloom.bloom_read_retained_rows(self.tc_ids)
        self.tc_before_table = self.bloom.bloom_read_cli_session_table()

        self.tc_commands.append(
            self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        )
        self.tc_heads = self.bloom.bloom_list_alembic_heads()
        self.tc_upgraded_revision = self.bloom.bloom_read_revision()
        self.tc_upgraded_rows = self.bloom.bloom_read_retained_rows(self.tc_ids)
        self.tc_upgraded_table = self.bloom.bloom_read_cli_session_table()

        self.bloom.bloom_add_cli_sessions(self.tc_ids["user"])
        self.tc_stored_sessions = self.bloom.bloom_read_cli_session_table()["sessions"]

        self.tc_commands.append(
            self.bloom.bloom_run_alembic("downgrade", self.parameters.MIGRATION_BEFORE_CLI)
        )
        self.tc_downgraded_revision = self.bloom.bloom_read_revision()
        self.tc_downgraded_rows = self.bloom.bloom_read_retained_rows(self.tc_ids)
        self.tc_downgraded_table = self.bloom.bloom_read_cli_session_table()

        self.tc_commands.append(
            self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        )
        self.tc_reupgraded_revision = self.bloom.bloom_read_revision()
        self.tc_reupgraded_rows = self.bloom.bloom_read_retained_rows(self.tc_ids)
        self.tc_reupgraded_table = self.bloom.bloom_read_cli_session_table()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthMigrationRoundTripTest().run()
