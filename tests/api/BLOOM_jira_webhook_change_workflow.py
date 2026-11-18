"""
* @file     ${tests/api/BLOOM_jira_webhook_change_workflow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A Jira closure outside the change request workflow is refused.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests a signed closure of change requests in Draft, Review and Approved.
"""

from tests.api.jira_webhook_change_workflow import JiraWebhookChangeWorkflowBase


class JiraWebhookChangeWorkflowTest(JiraWebhookChangeWorkflowBase):

    def setUpClass(self):
        super().setUpClass()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookChangeWorkflowTest().run()
