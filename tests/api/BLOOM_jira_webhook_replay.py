"""
* @file     ${tests/api/BLOOM_jira_webhook_replay.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A replayed Jira delivery is ignored.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one signed closure sent again after the defect was reopened in Bloom.
"""

from tests.api.jira_webhook_replay import JiraWebhookReplayBase


class JiraWebhookReplayTest(JiraWebhookReplayBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment()
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER)
        )
        self.bloom.bloom_post_jira_webhook(body, delivery=self.parameters.DELIVERIES[4])
        self.bloom.bloom_set_defect_status(self.tc_env.defect_id, self.parameters.DEFECT_OPEN)
        self.tc_replay = self.bloom.bloom_post_jira_webhook(
            body, delivery=self.parameters.DELIVERIES[4]
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookReplayTest().run()
