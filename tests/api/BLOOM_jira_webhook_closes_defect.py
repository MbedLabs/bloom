"""
* @file     ${tests/api/BLOOM_jira_webhook_closes_defect.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A signed Jira webhook closes the linked defect.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one signed update of the issue linked to a defect.
"""

from tests.api.jira_webhook_closes_defect import JiraWebhookClosesDefectBase


class JiraWebhookClosesDefectTest(JiraWebhookClosesDefectBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment()
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER)
        )
        self.tc_response = self.bloom.bloom_post_jira_webhook(
            body, delivery=self.parameters.DELIVERIES[0]
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookClosesDefectTest().run()
