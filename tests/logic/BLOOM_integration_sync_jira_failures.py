"""
* @file     ${tests/logic/BLOOM_integration_sync_jira_failures.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Failed Jira sync runs keep the last success.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests a Jira sync refused for its account, then one with Jira unreachable.
"""

from tests.logic.integration_sync_jira_failures import IntegrationSyncJiraFailuresBase


class IntegrationSyncJiraFailuresTest(IntegrationSyncJiraFailuresBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_before = self.parameters.NOW - self.parameters.LAST_SYNC
        created, updated = self.parameters.PREVIOUS_COUNTS
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(
            self.tc_project_id,
            synced_at=self.tc_before,
            sync_created=created,
            sync_updated=updated,
            sync_full_scan=False,
        )
        self.bloom.bloom_refuse_with(self.parameters.STATUS_UNAUTHORIZED)
        self.bloom.bloom_run_sync(self.parameters.NOW)
        self.tc_refused = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.bloom.bloom_make_unreachable()
        self.bloom.bloom_run_sync(self.parameters.NOW + self.parameters.LATER)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncJiraFailuresTest().run()
