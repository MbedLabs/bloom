"""
* @file     ${tests/logic/BLOOM_integration_sync_failing_setting.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A failing integration does not stop the sync of the next one.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one sync pass over two Jira integrations, the first failing.
"""

from tests.logic.integration_sync_failing_setting import (
    IntegrationSyncFailingSettingBase,
)


class IntegrationSyncFailingSettingTest(IntegrationSyncFailingSettingBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_failing_setting_id = self.bloom.bloom_create_integration(
            self.bloom.bloom_create_project(self.parameters.SYNC_PROJECT_PREFIX)
        )
        self.tc_other_setting_id = self.bloom.bloom_create_integration(
            self.bloom.bloom_create_project(self.parameters.SYNC_OTHER_PREFIX),
            jira_project_key=self.parameters.JIRA_OTHER_PROJECT,
        )
        self.bloom.bloom_fail_search_of(self.parameters.JIRA_PROJECT, self.parameters.FAILURE_TEXT)
        self.bloom.bloom_serve_jira()
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncFailingSettingTest().run()
