"""
* @file     ${tests/logic/BLOOM_campaign_sync_results.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A synced result updates its test case unless it is older; payloads are bounded.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests a latest result, an older result and an oversize payload.
"""

from tests.logic.campaign_sync_results import CampaignSyncResultsBase


class CampaignSyncResultsTest(CampaignSyncResultsBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_latest = self.bloom.bloom_apply_test_result(
            self.parameters.SYNC_RESULT_EMPTY_CASE, self.parameters.SYNC_RESULT_FAILED
        )
        self.tc_older = self.bloom.bloom_apply_test_result(
            self.parameters.SYNC_RESULT_NEWER_CASE, self.parameters.SYNC_RESULT_OLDER
        )
        self.tc_too_many = self.bloom.bloom_build_sync_request(
            self.parameters.SYNC_RESULT_TC_ID,
            self.parameters.SYNC_RESULT_STATUS,
            self.parameters.SYNC_RESULT_TOO_MANY,
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CampaignSyncResultsTest().run()
