"""
* @file     ${tests/api/BLOOM_jira_webhook_copies_issue.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A defect created from a Jira issue copies the issue.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one create delivery naming a Bloom test case, sent by the integration's Jira account.
"""

from tests.api.jira_webhook_copies_issue import JiraWebhookCopiesIssueBase


class JiraWebhookCopiesIssueTest(JiraWebhookCopiesIssueBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment(
            jira_project_key=self.parameters.JIRA_PROJECT, create_defects_on_inbound=True
        )
        tc_id = f"{self.parameters.SYNC_PROJECT_PREFIX}-TC-{self.parameters.TC_NUMBER:03d}"
        self.tc_test_case_id = self.bloom.bloom_add_test_case(
            self.tc_env.project_id, tc_id, self.parameters.TC_TITLE
        )
        self.tc_bot_id = self.bloom.bloom_add_user(
            self.parameters.BOT_EMAIL, self.bloom.bloom_maintainer_role()
        )
        self.tc_description = f"{self.parameters.DESCRIPTION_TEXT} {tc_id}"
        self.tc_key = self.bloom.bloom_jira_key(self.parameters.WEBHOOK_NEW_NUMBER)
        description = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": self.tc_description}]}
            ],
        }
        body = self.bloom.bloom_jira_webhook_body(
            self.tc_key,
            event=self.parameters.ISSUE_CREATED,
            status={
                "name": self.parameters.JIRA_TO_DO,
                "statusCategory": {"key": self.parameters.JIRA_NEW},
            },
            description=description,
            priority={"name": self.parameters.JIRA_HIGHEST},
        )
        self.tc_response = self.bloom.bloom_post_jira_webhook(
            body, delivery=self.parameters.DELIVERIES[0]
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookCopiesIssueTest().run()
