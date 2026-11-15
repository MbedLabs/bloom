"""
* @file     ${tests/api/BLOOM_jira_webhook_deleted_issue.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A deleted Jira issue keeps its defect and change request, marked removed.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests the deletion of the issues linked to a defect and to a change request.
"""

from tests.api.jira_webhook_deleted_issue import JiraWebhookDeletedIssueBase


class JiraWebhookDeletedIssueTest(JiraWebhookDeletedIssueBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment()
        defect_gone = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER),
            event=self.parameters.ISSUE_DELETED,
        )
        change_gone = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.CHANGE_NUMBER),
            event=self.parameters.ISSUE_DELETED,
        )
        self.tc_response = self.bloom.bloom_post_jira_webhook(
            defect_gone, delivery=self.parameters.DELIVERIES[7]
        )
        self.bloom.bloom_post_jira_webhook(change_gone, delivery=self.parameters.DELIVERIES[8])

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookDeletedIssueTest().run()
