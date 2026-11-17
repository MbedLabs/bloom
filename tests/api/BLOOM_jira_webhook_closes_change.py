"""
* @file     ${tests/api/BLOOM_jira_webhook_closes_change.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A signed Jira webhook closes the linked change request once.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one signed update of the issue linked to a change request, sent twice.
"""

from tests.api.jira_webhook_closes_change import JiraWebhookClosesChangeBase


class JiraWebhookClosesChangeTest(JiraWebhookClosesChangeBase):

    def setUpClass(self):
        super().setUpClass()
        self.env = self.bloom.bloom_create_webhook_environment()
        self.body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.CHANGE_NUMBER)
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookClosesChangeTest().run()
