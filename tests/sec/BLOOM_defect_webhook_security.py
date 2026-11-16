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
        github = bloom.bloom_link_defect(project, "github", repo, number)
        gitlab = bloom.bloom_link_defect(project, "gitlab", repo, values.HOOK_GITLAB_NUMBER)
        bloom.bloom_create_webhook_integration(project, tracker="github")
        bloom.bloom_create_webhook_integration(project, tracker="gitlab")
        bloom.bloom_start_api()
        post = bloom.bloom_post_github_webhook
        body = bloom.bloom_github_issue_body(number, repo)
        oversized = bloom.bloom_oversized_webhook_body()
        self.unsigned = post(body)
        self.wrong = post(body, signature=values.HOOK_WRONG_SIGNATURE)
        self.no_delivery = post(body, signature=bloom.bloom_sign(body))
        self.oversized = post(
            oversized, bloom.bloom_sign(oversized), values.HOOK_OVERSIZED_DELIVERY
        )
        self.status_after_refusals = bloom.bloom_get_defect(github).status
        self.successes_after_refusals = [
            event.id for event in bloom.bloom_list_defect_events() if event.success
        ]
        self.valid = post(body, bloom.bloom_sign(body), values.HOOK_DELIVERY)
        self.status_after_valid = bloom.bloom_get_defect(github).status
        self.replay = post(body, bloom.bloom_sign(body), values.HOOK_DELIVERY)
        self.gitlab_unsigned = bloom.bloom_post_gitlab_webhook(values.HOOK_GITLAB_NUMBER, repo)
        self.gitlab_status = bloom.bloom_get_defect(gitlab).status
        self.gitlab_valid = bloom.bloom_post_gitlab_webhook(
            values.HOOK_GITLAB_NUMBER, repo, values.WEBHOOK_SECRET, values.HOOK_GITLAB_DELIVERY
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DefectWebhookSecurityTest().run()
