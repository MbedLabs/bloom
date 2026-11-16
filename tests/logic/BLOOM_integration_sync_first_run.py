"""
* @file     ${tests/logic/BLOOM_integration_sync_first_run.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The first scheduled Jira sync creates the backlog and clears the full scan.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests the first Jira sync of an integration with one linked defect.
"""

from tests.logic.integration_sync_first_run import IntegrationSyncFirstRunBase


class IntegrationSyncFirstRunTest(IntegrationSyncFirstRunBase):

    def setUpClass(self):
        super().setUpClass()
        self.project_id = self.bloom.bloom_create_project()
        self.setting_id = self.bloom.bloom_create_integration(self.project_id)
        self.linked_defect_id = self.bloom.bloom_link_defect(
            self.project_id, "jira", self.parameters.JIRA_PROJECT, self.parameters.LINKED_NUMBER
        )
        self.bloom.bloom_serve_jira(
            creation=[
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.NEW_NUMBER),
                    summary=self.parameters.NEW_SUMMARY,
                ),
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER)
                ),
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.TASK_NUMBER),
                    kind=self.parameters.TASK,
                ),
            ]
        )
        self.synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncFirstRunTest().run()
