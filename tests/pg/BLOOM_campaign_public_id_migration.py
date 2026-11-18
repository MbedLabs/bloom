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
        self.prepared = self.bloom.bloom_run_alembic("upgrade", self.parameters.PUBLIC_ID_BEFORE)
        self.ids = self.bloom.bloom_seed_campaigns(self.parameters.CAMPAIGN_SEEDS)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CampaignPublicIdMigrationTest().run()
