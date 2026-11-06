"""
* @file     ${tests/api/BLOOM_jira_webhook_ignored_deliveries.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Unlinked issues, other events and malformed keys are not applied.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests three signed deliveries that match nothing in Bloom.
"""

from tests.api.jira_webhook_ignored_deliveries import JiraWebhookIgnoredDeliveriesBase


class JiraWebhookIgnoredDeliveriesTest(JiraWebhookIgnoredDeliveriesBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookIgnoredDeliveriesTest().run()
