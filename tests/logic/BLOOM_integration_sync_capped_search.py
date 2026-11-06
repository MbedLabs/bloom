"""
* @file     ${tests/logic/BLOOM_integration_sync_capped_search.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A capped Jira search continues on the next run.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests two Jira sync runs with searches capped, Jira answering in other zones.
"""

from datetime import timedelta

from tests.logic.integration_sync_capped_search import IntegrationSyncCappedSearchBase


class IntegrationSyncCappedSearchTest(IntegrationSyncCappedSearchBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id)
        self.bloom.bloom_cap_searches(self.parameters.SEARCH_CAP)
        self.tc_first_updated = self.parameters.NOW - self.parameters.LAST_SYNC
        self.tc_second_updated = self.tc_first_updated + timedelta(
            minutes=self.parameters.OVERLAP_MINUTES
        )
        first_key = self.bloom.bloom_jira_key(self.parameters.NEW_NUMBER)
        second_key = self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER)
        self.bloom.bloom_serve_jira(
            creation=[
                self.bloom.bloom_build_jira_issue(
                    first_key,
                    created=self.bloom.bloom_jira_time(
                        self.parameters.FIRST_CREATED, self.parameters.CREATED_OFFSET
                    ),
                ),
                self.bloom.bloom_build_jira_issue(
                    second_key,
                    created=self.bloom.bloom_jira_time(
                        self.parameters.SECOND_CREATED, self.parameters.CREATED_OFFSET
                    ),
                ),
            ],
            changed=[
                self.bloom.bloom_build_jira_issue(
                    first_key,
                    updated=self.bloom.bloom_jira_time(
                        self.tc_first_updated, self.parameters.UPDATED_OFFSET
                    ),
                ),
                self.bloom.bloom_build_jira_issue(
                    second_key,
                    updated=self.bloom.bloom_jira_time(
                        self.tc_second_updated, self.parameters.UPDATED_OFFSET
                    ),
                ),
            ],
        )
        self.bloom.bloom_run_sync(self.parameters.NOW)
        self.tc_first_run = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.bloom.bloom_run_sync(self.parameters.NOW + self.parameters.LATER)
        self.tc_next_creation = [
            q for q in self.bloom.site.jql if self.parameters.CREATION_MARK in q
        ][1]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncCappedSearchTest().run()
