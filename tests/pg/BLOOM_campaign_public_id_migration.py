"""
* @file     ${tests/pg/BLOOM_campaign_public_id_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Every campaign gets a public ID and suite and campaign public IDs become unique.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests the migration on new PostgreSQL seeded at the revision before.
"""

from tests.pg.campaign_public_id_migration import CampaignPublicIdMigrationBase


class CampaignPublicIdMigrationTest(CampaignPublicIdMigrationBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.postgres:
            return
        self.commands = [self.bloom.bloom_run_alembic("upgrade", self.parameters.PUBLIC_ID_BEFORE)]
        self.ids = self.bloom.bloom_seed_campaigns(self.parameters.CAMPAIGN_SEEDS)

        self.commands.append(
            self.bloom.bloom_run_alembic("upgrade", self.parameters.PUBLIC_ID_REVISION)
        )
        self.public_ids = self.bloom.bloom_read_campaign_public_ids()
        self.upgraded_shape = self.bloom.bloom_read_public_id_shape()
        self.violations = self.bloom.bloom_try_public_id_inserts(
            self.parameters.TAKEN_PREFIX,
            self.parameters.DUPLICATE_SUITE_ID,
            self.parameters.CAMPAIGN_EXPECTED[self.parameters.TAKEN_PREFIX][1],
        )

        self.commands.append(
            self.bloom.bloom_run_alembic("downgrade", self.parameters.PUBLIC_ID_BEFORE)
        )
        self.downgraded_shape = self.bloom.bloom_read_public_id_shape()
        self.downgraded_ids = self.bloom.bloom_read_campaign_public_ids()

        self.commands.append(
            self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        )
        self.reupgraded_shape = self.bloom.bloom_read_public_id_shape()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CampaignPublicIdMigrationTest().run()
