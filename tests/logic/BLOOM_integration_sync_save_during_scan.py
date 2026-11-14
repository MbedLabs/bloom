"""
* @file     ${tests/logic/BLOOM_integration_sync_save_during_scan.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A save during a full scan keeps the rescan.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests a Jira sync run while the integration is saved between search and write.
"""

from tests.logic.integration_sync_save_during_scan import (
    IntegrationSyncSaveDuringScanBase,
)


class IntegrationSyncSaveDuringScanTest(IntegrationSyncSaveDuringScanBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id)
        self.bloom.bloom_save_during_search(
            self.tc_setting_id,
            self.parameters.LABEL,
            self.parameters.NOW + self.parameters.SAVE_OFFSET,
        )
        self.bloom.bloom_serve_jira()
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncSaveDuringScanTest().run()
