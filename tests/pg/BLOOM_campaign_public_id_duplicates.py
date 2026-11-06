"""
* @file     ${tests/pg/BLOOM_campaign_public_id_duplicates.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The public ID migration stops while two suites or two campaigns share a public ID.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one new PostgreSQL database per duplicated column.
"""

from tests.pg.campaign_public_id_duplicates import CampaignPublicIdDuplicatesBase


class CampaignPublicIdDuplicatesTest(CampaignPublicIdDuplicatesBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.tc_postgres:
            return
        prefixes = self.parameters.CAMPAIGN_PREFIXES[:2]
        self.tc_refusals = []
        for suites, campaigns, _ in self.parameters.PUBLIC_ID_DUPLICATES:
            self.bloom.bloom_use_postgres(tables=False)
            self.bloom.bloom_run_alembic("upgrade", self.parameters.PUBLIC_ID_BEFORE)
            self.bloom.bloom_seed_public_id_pairs(prefixes, suites, campaigns)
            code, output = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
            self.tc_refusals.append((code, output, self.bloom.bloom_read_revision()))

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CampaignPublicIdDuplicatesTest().run()
