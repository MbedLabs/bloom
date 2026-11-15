"""
* @file     ${tests/logic/BLOOM_integration_sync_lifespan.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The application starts the sync loop unless the sync is switched off.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests the application lifespan with a sync rate, with none, and switched off.
"""

from tests.logic.integration_sync_lifespan import IntegrationSyncLifespanBase


class IntegrationSyncLifespanTest(IntegrationSyncLifespanBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_starts = [
            self.bloom.bloom_count_lifespan_starts(minutes)
            for minutes, _ in self.parameters.LIFESPAN_SWITCHES
        ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncLifespanTest().run()
