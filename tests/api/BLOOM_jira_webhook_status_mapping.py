"""
* @file     ${tests/api/BLOOM_jira_webhook_status_mapping.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Only closing and reopening in Jira change a defect's Bloom status.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests four signed updates of a linked defect, in order.
"""

from tests.api.jira_webhook_status_mapping import JiraWebhookStatusMappingBase


class JiraWebhookStatusMappingTest(JiraWebhookStatusMappingBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment()
        key = self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER)
        in_review = {
            "name": self.parameters.JIRA_IN_REVIEW,
            "statusCategory": {"key": self.parameters.JIRA_IN_PROGRESS_CATEGORY},
        }
        self.tc_in_review = self.bloom.bloom_jira_webhook_body(key, status=in_review)
        self.tc_done = self.bloom.bloom_jira_webhook_body(key)
        self.tc_in_review_renamed = self.bloom.bloom_jira_webhook_body(
            key, status=in_review, summary=self.parameters.SAME_SUMMARY
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookStatusMappingTest().run()
