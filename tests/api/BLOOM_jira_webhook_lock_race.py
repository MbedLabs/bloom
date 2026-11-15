"""
* @file     ${tests/api/BLOOM_jira_webhook_lock_race.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A defect linked while the delivery waited for the lock is followed, not doubled.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one create delivery while another sync links the same issue first.
"""

from tests.api.jira_webhook_lock_race import JiraWebhookLockRaceBase


class JiraWebhookLockRaceTest(JiraWebhookLockRaceBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment(
            jira_project_key=self.parameters.JIRA_PROJECT, create_defects_on_inbound=True
        )
        self.bloom.bloom_link_defect_before_reserving(
            self.tc_env.project_id, self.parameters.RACE_NUMBER, self.parameters.OLD_TITLE
        )
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.RACE_NUMBER),
            status={
                "name": self.parameters.JIRA_TO_DO,
                "statusCategory": {"key": self.parameters.JIRA_NEW},
            },
            summary=self.parameters.NEW_SUMMARY,
        )
        self.tc_response = self.bloom.bloom_post_jira_webhook(
            body, delivery=self.parameters.DELIVERIES[9]
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraWebhookLockRaceTest().run()
