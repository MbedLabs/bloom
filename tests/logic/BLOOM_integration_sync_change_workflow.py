"""
* @file     ${tests/logic/BLOOM_integration_sync_change_workflow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A change request in its workflow keeps its status when its Jira issue closes.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests the Jira sync of an approved and a submitted change request.
"""

from tests.logic.integration_sync_change_workflow import (
    IntegrationSyncChangeWorkflowBase,
)


class IntegrationSyncChangeWorkflowTest(IntegrationSyncChangeWorkflowBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(
            self.tc_project_id, sync_full_scan=False
        )
        self.tc_approved_id = self.bloom.bloom_link_change(
            self.tc_project_id,
            "jira",
            self.parameters.JIRA_PROJECT,
            self.parameters.LINKED_NUMBER,
            self.parameters.CHANGE_APPROVED,
        )
        self.tc_submitted_id = self.bloom.bloom_link_change(
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
                ),
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.CHANGE_NUMBER),
                    resolution={"name": self.parameters.JIRA_FIXED},
                ),
            ]
        )
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncChangeWorkflowTest().run()
