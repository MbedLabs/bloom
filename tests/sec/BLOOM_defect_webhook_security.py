"""
* @file     ${tests/sec/BLOOM_defect_webhook_security.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A tracker delivery changes a defect only when it is signed, identified and of a normal size.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the GitHub and GitLab webhooks with one linked defect each.
"""

from tests.sec.defect_webhook_security import DefectWebhookSecurityBase


class DefectWebhookSecurityTest(DefectWebhookSecurityBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        repo, number = values.REPO, values.HOOK_GITHUB_NUMBER
        project = bloom.bloom_create_project()
        self.github = bloom.bloom_link_defect(project, "github", repo, number)
        self.gitlab = bloom.bloom_link_defect(project, "gitlab", repo, values.HOOK_GITLAB_NUMBER)
        bloom.bloom_create_webhook_integration(project, tracker="github")
        bloom.bloom_create_webhook_integration(project, tracker="gitlab")
        bloom.bloom_start_api()
        self.body = bloom.bloom_github_issue_body(number, repo)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DefectWebhookSecurityTest().run()
