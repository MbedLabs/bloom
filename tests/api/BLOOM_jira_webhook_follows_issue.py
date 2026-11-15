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
        self.tc_env = self.bloom.bloom_create_webhook_environment()
        key = self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER)
        edit = self.bloom.bloom_jira_webhook_body(
            key,
            status={
                "name": self.parameters.JIRA_TO_DO,
                "statusCategory": {"key": self.parameters.JIRA_NEW},
            },
            summary=self.parameters.CHANGED_TITLE,
            description=self.parameters.CHANGED_DESCRIPTION,
            priority={"name": self.parameters.JIRA_PRIORITY},
        )
        self.tc_edit = self.bloom.bloom_post_jira_webhook(
            edit, delivery=self.parameters.DELIVERIES[5]
        )
        self.tc_after_edit = self.bloom.bloom_get_defect(self.tc_env.defect_id)
        in_review = {
            "name": self.parameters.JIRA_IN_REVIEW,
            "statusCategory": {"key": self.parameters.JIRA_IN_PROGRESS_CATEGORY},
        }
        resolved = self.bloom.bloom_jira_webhook_body(
            key, status=in_review, resolution={"name": self.parameters.JIRA_FIXED}
        )
        self.bloom.bloom_post_jira_webhook(resolved, delivery=self.parameters.DELIVERIES[6])

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookFollowsIssueTest().run()
