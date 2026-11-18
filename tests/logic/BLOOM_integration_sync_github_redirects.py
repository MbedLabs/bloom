"""
* @file     ${tests/logic/BLOOM_integration_sync_github_redirects.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    GitHub redirects are followed only on GitHub's API host.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests two GitHub sync runs: a move inside GitHub's API, then one to another host.
"""

from tests.logic.integration_sync_github_redirects import (
    IntegrationSyncGithubRedirectsBase,
)


class IntegrationSyncGithubRedirectsTest(IntegrationSyncGithubRedirectsBase):

    def setUpClass(self):
        super().setUpClass()
        number = self.parameters.GIT_NUMBERS[0]
        issues = [{"number": number, "state": self.parameters.GIT_CLOSED}]
        self.project_id = self.bloom.bloom_create_project()
        self.setting_id = self.bloom.bloom_create_integration(self.project_id, "github")
        self.defect_id = self.bloom.bloom_link_defect(
            self.project_id, "github", self.parameters.REPO, number
        )
        self.bloom.bloom_serve_redirect(
            self.parameters.REPO, self.parameters.MOVED, self.parameters.REDIRECTED, issues
        )
        self.bloom.bloom_run_sync(self.parameters.NOW)
        self.first_status = self.bloom.bloom_get_defect(self.defect_id).status
        first_calls = len(self.bloom.site.calls)
        self.bloom.bloom_serve_redirect(
            self.parameters.REPO, self.parameters.MOVED, self.parameters.FOREIGN, issues
        )
        self.bloom.bloom_run_sync(self.parameters.NOW + self.parameters.LATER)
        self.second_calls = len(self.bloom.site.calls) - first_calls

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncGithubRedirectsTest().run()
