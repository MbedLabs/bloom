"""
* @file     ${tests/api/BLOOM_jira_webhook_inbound_off.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    With creation off an unmatched Jira issue is not found.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one create delivery of a mapped project with creation off.
"""

from tests.api.jira_webhook_inbound_off import JiraWebhookInboundOffBase


class JiraWebhookInboundOffTest(JiraWebhookInboundOffBase):

    def setUpClass(self):
        super().setUpClass()
        self.env = self.bloom.bloom_create_webhook_environment(
            jira_project_key=self.parameters.JIRA_PROJECT, create_defects_on_inbound=False
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookInboundOffTest().run()
