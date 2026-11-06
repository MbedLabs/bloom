"""
* @file     ${tests/logic/BLOOM_integration_sync_later_run.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A later Jira sync searches its window and carries Jira's changes onto linked records.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests a Jira sync after a success, with a linked defect and change request.
"""

from tests.logic.integration_sync_later_run import IntegrationSyncLaterRunBase


class IntegrationSyncLaterRunTest(IntegrationSyncLaterRunBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(
            self.tc_project_id,
            sync_full_scan=False,
            synced_at=self.parameters.NOW - self.parameters.LAST_SYNC,
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
            changed=[
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER),
                    category=self.parameters.JIRA_DONE_CATEGORY,
                    status=self.parameters.JIRA_DONE,
                    summary=self.parameters.CHANGED_TITLE,
                    description=self.parameters.CHANGED_DESCRIPTION,
                    priority={"name": self.parameters.JIRA_PRIORITY},
                    resolution={"name": self.parameters.JIRA_DONE},
                ),
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.CHANGE_NUMBER),
                    category=self.parameters.JIRA_DONE_CATEGORY,
                    status=self.parameters.JIRA_DONE,
                ),
            ]
        )
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncLaterRunTest().run()
