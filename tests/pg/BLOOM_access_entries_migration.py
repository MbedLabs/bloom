"""
* @file     ${tests/pg/BLOOM_access_entries_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The access-entries migration seeds the default policies and groups and converts the 1.1.0 project memberships.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests a PostgreSQL database migrated from the revision before the access entries, then runs the access suites on it.
"""

from tests.pg.access_entries_migration import AccessEntriesMigrationBase


class AccessEntriesMigrationTest(AccessEntriesMigrationBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.postgres:
            return
        self.bloom.bloom_new_migration_database()
        self.bloom.bloom_run_alembic("upgrade", self.parameters.AEM_BEFORE)
        self.ids = self.bloom.bloom_seed_released_memberships()
        self.bloom.bloom_run_alembic("upgrade", "head")
        self.state = self.bloom.bloom_access_state()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AccessEntriesMigrationTest().run()
