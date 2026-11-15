"""
* @file     ${tests/api/BLOOM_jira_pull_missing_defects.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Sync now creates the missing defects from Jira's search pages.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests Sync now over two search pages with a linked issue, a new Bug, a Task and a bad key.
"""

from tests.api.jira_pull_missing_defects import JiraPullMissingDefectsBase


class JiraPullMissingDefectsTest(JiraPullMissingDefectsBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment(
            jira_project_key=self.parameters.JIRA_PROJECT, create_defects_on_inbound=True
        )
        bug = {"name": self.parameters.BUG}
        pages = [
            {
                "issues": [
                    {
                        "key": self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER),
                        "fields": {"issuetype": bug, "summary": self.parameters.OLD_TITLE},
                    },
                    {
                        "key": self.bloom.bloom_jira_key(self.parameters.PULL_NEW_NUMBER),
                        "fields": {"issuetype": bug, "summary": self.parameters.NEW_SUMMARY},
                    },
                ],
                "nextPageToken": self.parameters.NEXT_PAGE_TOKEN,
                "isLast": False,
            },
            {
                "issues": [
                    {
                        "key": self.bloom.bloom_jira_key(self.parameters.PULL_TASK_NUMBER),
                        "fields": {"issuetype": {"name": self.parameters.TASK}},
                    },
                    {"key": self.parameters.MALFORMED_KEY, "fields": {"issuetype": bug}},
                ],
                "isLast": True,
            },
        ]
        self.tc_seen = self.bloom.bloom_serve_jira_pages(pages)
        self.tc_result = self.bloom.bloom_sync_now(
            self.tc_env.setting_id, self.parameters.ADMIN_EMAIL
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraPullMissingDefectsTest().run()
