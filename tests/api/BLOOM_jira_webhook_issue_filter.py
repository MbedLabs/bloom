"""
* @file     ${tests/api/BLOOM_jira_webhook_issue_filter.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Issues outside the project's filter are ignored.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests a Task, an unlabelled and a labelled Bug, and the deletion of an unknown issue.
"""

from tests.api.jira_webhook_issue_filter import JiraWebhookIssueFilterBase


class JiraWebhookIssueFilterTest(JiraWebhookIssueFilterBase):

    def setUpClass(self):
        super().setUpClass()
        self.env = self.bloom.bloom_create_webhook_environment(
            jira_project_key=self.parameters.JIRA_PROJECT, create_defects_on_inbound=True
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookIssueFilterTest().run()
