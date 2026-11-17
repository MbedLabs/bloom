"""
* @file     ${tests/api/BLOOM_sync_results_names_the_campaign.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Bloom tells Bud which campaign the synced results reached.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the result sync on the full application; each step uses its own project.
"""

from tests.api.sync_results_names_the_campaign import SyncResultsNamesTheCampaignBase


class SyncResultsNamesTheCampaignTest(SyncResultsNamesTheCampaignBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.bloom.bloom_allow_bud_sync()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    SyncResultsNamesTheCampaignTest().run()
