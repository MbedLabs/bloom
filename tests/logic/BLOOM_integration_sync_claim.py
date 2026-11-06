"""
* @file     ${tests/logic/BLOOM_integration_sync_claim.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A second claim of an integration's sync within its rate loses.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests three claims of one integration's sync, the last after the rate.
"""

from tests.logic.integration_sync_claim import IntegrationSyncClaimBase


class IntegrationSyncClaimTest(IntegrationSyncClaimBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncClaimTest().run()
