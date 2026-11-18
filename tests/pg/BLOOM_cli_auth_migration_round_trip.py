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
        self.prepared = self.bloom.bloom_run_alembic(
            "upgrade", self.parameters.MIGRATION_BEFORE_CLI
        )
        self.ids = self.bloom.bloom_seed_retained_rows()
        self.before_rows = self.bloom.bloom_read_retained_rows(self.ids)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthMigrationRoundTripTest().run()
