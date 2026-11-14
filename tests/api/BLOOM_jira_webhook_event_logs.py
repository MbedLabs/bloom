"""
* @file     ${tests/api/BLOOM_jira_webhook_event_logs.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Defect and change request sync events land in their own logs.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one sync event logged for a defect and one for a change request.
"""

from tests.api.jira_webhook_event_logs import JiraWebhookEventLogsBase


class JiraWebhookEventLogsTest(JiraWebhookEventLogsBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment()
        self.bloom.bloom_log_sync_event(
            self.parameters.TARGET_DEFECT, self.tc_env.defect_id, self.parameters.PROBE_DEFECT_EVENT
        )
        self.bloom.bloom_log_sync_event(
            self.parameters.TARGET_CHANGE, self.tc_env.change_id, self.parameters.PROBE_CHANGE_EVENT
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookEventLogsTest().run()
