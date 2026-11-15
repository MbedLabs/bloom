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
        self.tc_env = self.bloom.bloom_create_webhook_environment(
            jira_project_key=self.parameters.JIRA_PROJECT, create_defects_on_inbound=True
        )
        task, unlabelled, labelled, gone = (
            self.bloom.bloom_jira_key(number) for number in self.parameters.FILTER_NUMBERS
        )
        post = self.bloom.bloom_post_jira_webhook
        body = self.bloom.bloom_jira_webhook_body
        self.tc_task = post(
            body(
                task,
                event=self.parameters.ISSUE_CREATED,
                status={
                    "name": self.parameters.JIRA_TO_DO,
                    "statusCategory": {"key": self.parameters.JIRA_NEW},
                },
                issuetype={"name": self.parameters.TASK},
            ),
            delivery=self.parameters.DELIVERIES[1],
        )
        self.bloom.bloom_update_setting(self.tc_env.setting_id, jira_label=self.parameters.LABEL)
        self.tc_unlabelled = post(
            body(
                unlabelled,
                event=self.parameters.ISSUE_CREATED,
                status={
                    "name": self.parameters.JIRA_TO_DO,
                    "statusCategory": {"key": self.parameters.JIRA_NEW},
                },
            ),
            delivery=self.parameters.DELIVERIES[2],
        )
        self.tc_labelled = post(
            body(
                labelled,
                event=self.parameters.ISSUE_CREATED,
                status={
                    "name": self.parameters.JIRA_TO_DO,
                    "statusCategory": {"key": self.parameters.JIRA_NEW},
                },
                labels=[self.parameters.LABEL],
            ),
            delivery=self.parameters.DELIVERIES[3],
        )
        self.tc_gone = post(
            body(
                gone,
                event=self.parameters.ISSUE_DELETED,
                status={
                    "name": self.parameters.JIRA_TO_DO,
                    "statusCategory": {"key": self.parameters.JIRA_NEW},
                },
            ),
            delivery=self.parameters.DELIVERIES[4],
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookIssueFilterTest().run()
