"""
* @file     ${tests/logic/BLOOM_integration_sync_gitlab_hosts.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    GitLab is called on the configured base URL, else on gitlab.com.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one sync run over two GitLab integrations, one with a base URL.
"""

from tests.logic.integration_sync_gitlab_hosts import IntegrationSyncGitlabHostsBase


class IntegrationSyncGitlabHostsTest(IntegrationSyncGitlabHostsBase):

    def setUpClass(self):
        super().setUpClass()
        number = self.parameters.GIT_NUMBERS[0]
        self.tc_defect_ids = []
        for prefix, (base_url, _host) in zip(
            (self.parameters.SYNC_PROJECT_PREFIX, self.parameters.SYNC_OTHER_PREFIX),
            self.parameters.GITLAB_HOSTS,
        ):
            project_id = self.bloom.bloom_create_project(prefix)
            self.bloom.bloom_create_integration(project_id, "gitlab", base_url=base_url)
            self.tc_defect_ids.append(
                self.bloom.bloom_link_defect(project_id, "gitlab", self.parameters.REPO, number)
            )
        self.bloom.bloom_serve_issue_list([{"iid": number, "state": self.parameters.GIT_CLOSED}])
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncGitlabHostsTest().run()
