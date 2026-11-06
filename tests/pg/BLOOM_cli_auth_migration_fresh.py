"""
* @file     ${tests/pg/BLOOM_cli_auth_migration_fresh.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An empty database upgrades to the single head of the migrations.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one upgrade to head on a new, empty PostgreSQL database.
"""

from tests.pg.cli_auth_migration_fresh import CliAuthMigrationFreshBase


class CliAuthMigrationFreshTest(CliAuthMigrationFreshBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.tc_postgres:
            return
        self.tc_upgrade = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.tc_heads = self.bloom.bloom_list_alembic_heads()
        self.tc_revision = self.bloom.bloom_read_revision()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthMigrationFreshTest().run()
