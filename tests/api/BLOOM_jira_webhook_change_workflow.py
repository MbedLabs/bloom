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
        self.tc_results = []
        for index, status in enumerate(self.parameters.CHANGE_WORKFLOW_STATUSES):
            self.bloom.tearDown()
            self.bloom.setUp()
            env = self.bloom.bloom_create_webhook_environment(change_status=status)
            body = self.bloom.bloom_jira_webhook_body(
                self.bloom.bloom_jira_key(self.parameters.CHANGE_NUMBER)
            )
            response = self.bloom.bloom_post_jira_webhook(
                body, delivery=self.parameters.DELIVERIES[index]
            )
            self.tc_results.append((response, self.bloom.bloom_get_change(env.change_id).status))

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookChangeWorkflowTest().run()
