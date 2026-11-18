"""
* @file     ${tests/pg/BLOOM_pre_baseline_repair.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A database created before the locked baseline gets the column and table it lacks.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the repair statements on a migrated PostgreSQL database that lost the column and the table.
"""

from tests.pg.pre_baseline_repair import PreBaselineRepairBase


class PreBaselineRepairTest(PreBaselineRepairBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.postgres:
            return
        self.upgrade = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.repair = self.bloom.bloom_repair_pre_baseline_schema()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    PreBaselineRepairTest().run()
