"""
* @file     ${tests/logic/BLOOM_integration_sync_creation_off.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    With creation off the Jira sync creates nothing and still updates linked defects.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests the Jira sync of an integration that does not create defects.
"""

from tests.logic.integration_sync_creation_off import IntegrationSyncCreationOffBase


class IntegrationSyncCreationOffTest(IntegrationSyncCreationOffBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(
            self.tc_project_id, create_defects_on_inbound=False
        )
        self.tc_linked_defect_id = self.bloom.bloom_link_defect(
            self.tc_project_id, "jira", self.parameters.JIRA_PROJECT, self.parameters.LINKED_NUMBER
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
                    category=self.parameters.JIRA_DONE_CATEGORY,
                    status=self.parameters.JIRA_DONE,
                )
            ],
        )
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncCreationOffTest().run()
