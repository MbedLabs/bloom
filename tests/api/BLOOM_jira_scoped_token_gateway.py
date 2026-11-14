"""
* @file     ${tests/api/BLOOM_jira_scoped_token_gateway.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A scoped token is used through the Atlassian gateway.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests Sync now when the site refuses the token and the cloud gateway takes it.
"""

from tests.api.jira_scoped_token_gateway import JiraScopedTokenGatewayBase


class JiraScopedTokenGatewayTest(JiraScopedTokenGatewayBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment(
            jira_project_key=self.parameters.JIRA_PROJECT, create_defects_on_inbound=True
        )
        issue = {
            "key": self.bloom.bloom_jira_key(self.parameters.GATEWAY_NUMBER),
            "fields": {
                "issuetype": {"name": self.parameters.BUG},
                "summary": self.parameters.NEW_SUMMARY,
            },
        }
        self.bloom.bloom_serve_atlassian_gateway(self.parameters.CLOUD_ID, [issue])
        self.tc_result = self.bloom.bloom_sync_now(
            self.tc_env.setting_id, self.parameters.ADMIN_EMAIL
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraScopedTokenGatewayTest().run()
