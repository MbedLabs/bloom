"""
* @file     ${tests/pg/BLOOM_requirement_parent_drop_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The requirement parent migration drops requirements.parent_id and keeps every requirement.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the upgrade and the downgrade on a new PostgreSQL database holding a requirement with a parent.
"""

from tests.pg.requirement_parent_drop_migration import (
    RequirementParentDropMigrationBase,
)


class RequirementParentDropMigrationTest(RequirementParentDropMigrationBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.tc_postgres:
            return
        before = self.parameters.PARENT_BEFORE
        self.tc_before = self.bloom.bloom_run_alembic("upgrade", before)
        self.bloom.bloom_seed_requirement_with_parent(
            self.parameters.PARENT_PREFIX, self.parameters.PARENT_REQ_IDS
        )
        self.tc_upgrade = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.tc_upgraded = self.bloom.bloom_read_requirement_parent_state()
        self.tc_downgrade = self.bloom.bloom_run_alembic("downgrade", before)
        self.tc_downgraded = self.bloom.bloom_read_requirement_parent_state()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementParentDropMigrationTest().run()
