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
        self.postgres = self.bloom.bloom_use_postgres(tables=False)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CampaignPublicIdDuplicatesTest().run()
