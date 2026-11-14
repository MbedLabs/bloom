"""
* @file     ${tests/api/BLOOM_jira_webhook_spoofed_events.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A refused Jira delivery records no successful event.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests two forged deliveries, one per linked record.
"""

from tests.api.jira_webhook_spoofed_events import JiraWebhookSpoofedEventsBase


class JiraWebhookSpoofedEventsTest(JiraWebhookSpoofedEventsBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment()
        for number, delivery in (
            (self.parameters.LINKED_NUMBER, self.parameters.DELIVERIES[8]),
            (self.parameters.CHANGE_NUMBER, self.parameters.DELIVERIES[9]),
        ):
            body = self.bloom.bloom_jira_webhook_body(self.bloom.bloom_jira_key(number))
            self.bloom.bloom_post_jira_webhook(
                body, signature=self.parameters.FORGED_SIGNATURE, delivery=delivery
            )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookSpoofedEventsTest().run()
