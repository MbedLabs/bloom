"""
* @file     ${tests/pg/BLOOM_overlapping_project_groups_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Overlapping project groups migrate without losing access entries, and the downgrade waits until none overlaps.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the upgrade and the downgrade on a new PostgreSQL database holding five kinds of access entry.
"""

from tests.pg.overlapping_project_groups_migration import (
    OverlappingProjectGroupsMigrationBase,
)


class OverlappingProjectGroupsMigrationTest(OverlappingProjectGroupsMigrationBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.tc_postgres:
            return
        before, head = self.parameters.OVERLAP_BEFORE, self.parameters.MIGRATION_HEAD
        snapshot = self.bloom.bloom_snapshot_project_access
        self.tc_before = self.bloom.bloom_run_alembic("upgrade", before)
        seeded = self.bloom.bloom_seed_overlap_entries()
        self.tc_state_before = snapshot()
        self.tc_upgrade = self.bloom.bloom_run_alembic("upgrade", head)
        self.tc_after = snapshot()
        self.tc_overlap = self.bloom.bloom_add_overlapping_group(seeded)
        self.tc_overlapping = snapshot()
        self.tc_refused = self.bloom.bloom_run_alembic("downgrade", before)
        self.tc_after_refusal = snapshot()
        self.bloom.bloom_delete_access_entry(self.tc_overlap.entry)
        self.tc_downgrade = self.bloom.bloom_run_alembic("downgrade", before)
        self.tc_downgraded = snapshot()
        self.tc_upgrade_again = self.bloom.bloom_run_alembic("upgrade", head)
        self.tc_upgraded_again = snapshot()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    OverlappingProjectGroupsMigrationTest().run()
