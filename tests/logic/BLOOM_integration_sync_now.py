"""
* @file     ${tests/logic/BLOOM_integration_sync_now.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Sync now runs the whole Jira sync at once.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests Sync now pressed by an admin on an integration with creation off.
"""

from tests.logic.integration_sync_now import IntegrationSyncNowBase


class IntegrationSyncNowTest(IntegrationSyncNowBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(
            self.tc_project_id, create_defects_on_inbound=False
        )
        self.tc_defect_id = self.bloom.bloom_link_defect(
            self.tc_project_id, "jira", self.parameters.JIRA_PROJECT, self.parameters.LINKED_NUMBER
        )
        self.tc_change_id = self.bloom.bloom_link_change(
            self.tc_project_id,
            "jira",
            self.parameters.JIRA_PROJECT,
            self.parameters.CHANGE_NUMBER,
            self.parameters.CHANGE_SUBMITTED,
        )
        self.bloom.bloom_serve_jira(
            creation=[
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.NEW_NUMBER)
                )
            ],
            changed=[
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER),
                    summary=self.parameters.CHANGED_TITLE,
                )
            ],
            issue_status={
                self.bloom.bloom_jira_key(
                    self.parameters.CHANGE_NUMBER
                ): self.parameters.STATUS_SERVER_ERROR
            },
        )
        self.tc_result = self.bloom.bloom_sync_now(self.tc_setting_id, self.parameters.ADMIN_EMAIL)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncNowTest().run()
