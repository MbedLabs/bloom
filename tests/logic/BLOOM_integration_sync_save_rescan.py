"""
* @file     ${tests/logic/BLOOM_integration_sync_save_rescan.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Saving an integration asks for a full scan again.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests a Jira sync run followed by a save of the integration by an admin.
"""

from tests.logic.integration_sync_save_rescan import IntegrationSyncSaveRescanBase


class IntegrationSyncSaveRescanTest(IntegrationSyncSaveRescanBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id)
        self.bloom.bloom_serve_jira()
        self.bloom.bloom_run_sync(self.parameters.NOW)
        self.tc_after_run = self.bloom.bloom_get_setting(self.tc_setting_id).sync_full_scan
        self.bloom.bloom_save_setting(
            self.tc_setting_id, self.parameters.ADMIN_EMAIL, jira_label=self.parameters.LABEL
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncSaveRescanTest().run()
