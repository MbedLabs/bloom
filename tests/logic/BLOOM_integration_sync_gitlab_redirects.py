"""
* @file     ${tests/logic/BLOOM_integration_sync_gitlab_redirects.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    GitLab redirects are not followed.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one GitLab sync run against a server that redirects every call.
"""

from tests.logic.integration_sync_gitlab_redirects import (
    IntegrationSyncGitlabRedirectsBase,
)


class IntegrationSyncGitlabRedirectsTest(IntegrationSyncGitlabRedirectsBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(
            self.tc_project_id, "gitlab", base_url=f"https://{self.parameters.GITLAB_HOST}"
        )
        self.bloom.bloom_link_defect(
            self.tc_project_id, "gitlab", self.parameters.REPO, self.parameters.GIT_NUMBERS[0]
        )
        self.bloom.bloom_refuse_with(
            self.parameters.MOVED, headers={"location": self.parameters.FOREIGN}
        )
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncGitlabRedirectsTest().run()
