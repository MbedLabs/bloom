"""
* @file     ${tests/logic/BLOOM_integration_sync_now_capped.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Sync now continues a capped full search.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests Sync now pressed twice with the Jira search capped at one issue.
"""

from tests.logic.integration_sync_now_capped import IntegrationSyncNowCappedBase


class IntegrationSyncNowCappedTest(IntegrationSyncNowCappedBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id)
        self.bloom.bloom_cap_searches(self.parameters.SYNC_NOW_CAP)
        self.bloom.bloom_serve_jira(
            creation=[
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.NEW_NUMBER),
                    created=self.bloom.bloom_jira_time(
                        self.parameters.FIRST_CREATED, self.parameters.CREATED_OFFSET
                    ),
                )
            ]
        )
        self.bloom.bloom_sync_now(self.tc_setting_id, self.parameters.ADMIN_EMAIL)
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.tc_first_state = (setting.sync_full_scan, setting.sync_scan_from)
        self.bloom.bloom_sync_now(self.tc_setting_id, self.parameters.OTHER_ADMIN_EMAIL)
        self.tc_next_creation = [
            q for q in self.bloom.site.jql if self.parameters.CREATION_MARK in q
        ][1]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncNowCappedTest().run()
