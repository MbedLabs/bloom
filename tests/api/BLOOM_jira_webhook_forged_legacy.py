"""
* @file     ${tests/api/BLOOM_jira_webhook_forged_legacy.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A forged Jira delivery leaves a submitted change request open.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one forged closure of the issue linked to a change request.
"""

from tests.api.jira_webhook_forged_legacy import JiraWebhookForgedLegacyBase


class JiraWebhookForgedLegacyTest(JiraWebhookForgedLegacyBase):

    def setUpClass(self):
        super().setUpClass()
        self.env = self.bloom.bloom_create_webhook_environment()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookForgedLegacyTest().run()
