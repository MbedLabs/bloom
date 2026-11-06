"""
* @file     ${tests/logic/BLOOM_integration_sync_unreadable_repository.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An unreadable repository is skipped and named, and the warning clears once it reads again.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests two GitHub sync runs, the first with one repository answering 404.
"""

from tests.logic.integration_sync_unreadable_repository import (
    IntegrationSyncUnreadableRepositoryBase,
)


class IntegrationSyncUnreadableRepositoryTest(IntegrationSyncUnreadableRepositoryBase):

    def setUpClass(self):
        super().setUpClass()
        readable, unreadable, _, _ = self.parameters.GIT_NUMBERS
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id, "github")
        self.tc_readable_id = self.bloom.bloom_link_defect(
            self.tc_project_id, "github", self.parameters.REPO, readable
        )
        self.bloom.bloom_link_defect(
            self.tc_project_id, "github", self.parameters.OTHER_REPO, unreadable
        )
        issues = [{"number": readable, "state": self.parameters.GIT_CLOSED}]
        self.bloom.bloom_serve_issue_list(
            issues,
            unreadable_repo=self.parameters.OTHER_REPO,
            unreadable_status=self.parameters.STATUS_NOT_FOUND,
        )
        self.bloom.bloom_run_sync(self.parameters.NOW)
        self.tc_readable_status = self.bloom.bloom_get_defect(self.tc_readable_id).status
        self.tc_first_run = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.bloom.bloom_serve_issue_list(issues)
        self.bloom.bloom_run_sync(self.parameters.NOW + self.parameters.LATER)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncUnreadableRepositoryTest().run()
