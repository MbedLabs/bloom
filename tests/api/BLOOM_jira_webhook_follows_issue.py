"""
* @file     ${tests/api/BLOOM_jira_webhook_follows_issue.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A linked defect follows its issue and closes on resolution.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests an edit of the linked issue, then its resolution.
"""

from tests.api.jira_webhook_follows_issue import JiraWebhookFollowsIssueBase


class JiraWebhookFollowsIssueTest(JiraWebhookFollowsIssueBase):

    def setUpClass(self):
        super().setUpClass()
        self.env = self.bloom.bloom_create_webhook_environment()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookFollowsIssueTest().run()
