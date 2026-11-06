"""
* @file     ${tests/api/BLOOM_jira_webhook_inbound_creation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An unmatched Jira issue of a mapped project creates one defect.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests a create delivery of a mapped project, then the same delivery again.
"""

from tests.api.jira_webhook_inbound_creation import JiraWebhookInboundCreationBase


class JiraWebhookInboundCreationTest(JiraWebhookInboundCreationBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment(
            jira_project_key=self.parameters.JIRA_PROJECT, create_defects_on_inbound=True
        )
        to_do = {
            "name": self.parameters.JIRA_TO_DO,
            "statusCategory": {"key": self.parameters.JIRA_NEW},
        }
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.WEBHOOK_NEW_NUMBER),
            status=to_do,
            summary=self.parameters.NEW_SUMMARY,
        )
        self.tc_response = self.bloom.bloom_post_jira_webhook(
            body, delivery=self.parameters.DELIVERIES[10]
        )
        self.tc_replay = self.bloom.bloom_post_jira_webhook(
            body, delivery=self.parameters.DELIVERIES[10]
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookInboundCreationTest().run()
