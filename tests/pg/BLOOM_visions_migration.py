"""
* @file     ${tests/pg/BLOOM_visions_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The Visions migration reaches only its named holders and refuses to downgrade over visions.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the upgrade and the downgrade on a new PostgreSQL database holding two entries, a group and a hand-made policy.
"""

from tests.pg.visions_migration import VisionsMigrationBase


class VisionsMigrationTest(VisionsMigrationBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.postgres:
            return
        before, head = self.parameters.VISIONS_BEFORE, self.parameters.MIGRATION_HEAD
        self.before = self.bloom.bloom_run_alembic("upgrade", before)
        seeded = self.bloom.bloom_seed_visions_holders()
        self.state_before = self.bloom.bloom_read_visions_state(seeded)
        self.upgrade = self.bloom.bloom_run_alembic("upgrade", head)
        self.after = self.bloom.bloom_read_visions_state(seeded)
        vision = self.bloom.bloom_add_vision(seeded["project"])
        self.refused = self.bloom.bloom_run_alembic("downgrade", before)
        self.bloom.bloom_delete_document(vision)
        self.downgrade = self.bloom.bloom_run_alembic("downgrade", before)
        self.downgraded = self.bloom.bloom_read_visions_state(seeded)
        self.upgrade_again = self.bloom.bloom_run_alembic("upgrade", head)
        self.upgraded_again = self.bloom.bloom_read_visions_state(seeded)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    VisionsMigrationTest().run()
