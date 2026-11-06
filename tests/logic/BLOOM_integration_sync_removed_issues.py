"""
* @file     ${tests/logic/BLOOM_integration_sync_removed_issues.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Deleted Jira issues are marked removed and the removal cursor moves on.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests two Jira sync runs that each check one linked issue for removal.
"""

from tests.logic.integration_sync_removed_issues import IntegrationSyncRemovedIssuesBase


class IntegrationSyncRemovedIssuesTest(IntegrationSyncRemovedIssuesBase):

    def setUpClass(self):
        super().setUpClass()
        gone, forbidden = self.parameters.REMOVED_NUMBERS
        self.tc_gone_key = self.bloom.bloom_jira_key(gone)
        self.tc_forbidden_key = self.bloom.bloom_jira_key(forbidden)
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(
            self.tc_project_id, create_defects_on_inbound=False
        )
        self.tc_defect_id = self.bloom.bloom_link_defect(
            self.tc_project_id, "jira", self.parameters.JIRA_PROJECT, gone
        )
        self.tc_change_id = self.bloom.bloom_link_change(
            self.tc_project_id,
            "jira",
            self.parameters.JIRA_PROJECT,
            forbidden,
            self.parameters.CHANGE_SUBMITTED,
        )
        self.bloom.bloom_check_removals(self.parameters.REMOVAL_CHECKS)
        self.bloom.bloom_serve_jira(
            issue_status={
                self.tc_gone_key: self.parameters.STATUS_NOT_FOUND,
                self.tc_forbidden_key: self.parameters.STATUS_FORBIDDEN,
            }
        )
        self.bloom.bloom_run_sync(self.parameters.NOW)
        self.tc_first_reads = list(self.bloom.site.reads)
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.tc_first_cursor = (setting.sync_removal_cursor, setting.sync_updated)
        self.bloom.bloom_run_sync(self.parameters.NOW + self.parameters.LATER)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncRemovedIssuesTest().run()
