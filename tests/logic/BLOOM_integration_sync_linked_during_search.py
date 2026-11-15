"""
* @file     ${tests/logic/BLOOM_integration_sync_linked_during_search.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A defect linked during the Jira search is created once.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests the Jira sync while a defect is linked to the found issue.
"""

from tests.logic.integration_sync_linked_during_search import (
    IntegrationSyncLinkedDuringSearchBase,
)


class IntegrationSyncLinkedDuringSearchTest(IntegrationSyncLinkedDuringSearchBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id)
        self.bloom.bloom_link_defect_during_search(self.tc_project_id, self.parameters.NEW_NUMBER)
        self.bloom.bloom_serve_jira(
            creation=[
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.NEW_NUMBER)
                )
            ]
        )
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncLinkedDuringSearchTest().run()
