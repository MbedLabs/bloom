"""
* @file     ${tests/api/BLOOM_jira_webhook_signatures.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The Jira webhook refuses deliveries that are not signed and identified.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests four forged or incomplete deliveries of a linked issue.
"""

from tests.api.jira_webhook_signatures import JiraWebhookSignaturesBase


class JiraWebhookSignaturesTest(JiraWebhookSignaturesBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment()
        self.tc_body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER)
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookSignaturesTest().run()
