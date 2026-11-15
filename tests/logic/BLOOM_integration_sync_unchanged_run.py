"""
* @file     ${tests/logic/BLOOM_integration_sync_unchanged_run.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A Jira sync run that changes nothing writes no event and no update time.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests two Jira sync runs over an issue that does not change.
"""

from tests.logic.integration_sync_unchanged_run import IntegrationSyncUnchangedRunBase


class IntegrationSyncUnchangedRunTest(IntegrationSyncUnchangedRunBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(
            self.tc_project_id, sync_full_scan=False
        )
        self.tc_defect_id = self.bloom.bloom_link_defect(
            self.tc_project_id, "jira", self.parameters.JIRA_PROJECT, self.parameters.LINKED_NUMBER
        )
        self.tc_updated_at = self.bloom.bloom_get_setting(self.tc_setting_id).updated_at
        self.bloom.bloom_serve_jira(
            changed=[
                self.bloom.bloom_build_jira_issue(
                    self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER),
                    summary=self.parameters.SAME_SUMMARY,
                )
            ]
        )
        self.bloom.bloom_run_sync(self.parameters.NOW)
        self.tc_first_events = len(self.bloom.bloom_list_defect_events())
        self.bloom.bloom_run_sync(self.parameters.NOW + self.parameters.LATER)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncUnchangedRunTest().run()
