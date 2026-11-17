"""
* @file     ${tests/api/jira_webhook_copies_issue.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what a defect created from a Jira issue copies.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests what a defect created from a Jira issue copies.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraWebhookCopiesIssueBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_issue_creates_a_defect(self):
        description = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": self.description}]}
            ],
        }
        body = self.bloom.bloom_jira_webhook_body(
            self.key,
            event=self.parameters.ISSUE_CREATED,
            status={
                "name": self.parameters.JIRA_TO_DO,
                "statusCategory": {"key": self.parameters.JIRA_NEW},
            },
            description=description,
            priority={"name": self.parameters.JIRA_HIGHEST},
        )
        response = self.bloom.bloom_post_jira_webhook(body, delivery=self.parameters.DELIVERIES[0])
        self.print_variables({"answer": response.json()})
        self.assertEqual(
            response.json().get("status"),
            self.parameters.ANSWER_CREATED,
            msg=self.parameters.MSG_INBOUND_CREATED,
            abort_on_fail=False,
        )

    def bud_defect_copies_the_issue(self):
        defect = self.bloom.bloom_list_defects_linked_to(self.parameters.WEBHOOK_NEW_NUMBER)[0]
        found = (
            defect.description,
            defect.priority,
            defect.severity,
            defect.external_issue_url,
            defect.source_type,
            defect.source_id,
            defect.external_issue_state,
            defect.reporter_id,
        )
        self.print_variables({"defect": found})
        self.assertEqual(
            found,
            (
                self.description,
                self.parameters.CRITICAL,
                self.parameters.CRITICAL,
                f"{self.parameters.JIRA_URL}/browse/{self.key}",
                self.parameters.SOURCE_TC,
                self.test_case_id,
                self.parameters.JIRA_TO_DO,
                self.bot_id,
            ),
            msg=self.parameters.MSG_COPIES_ISSUE,
            abort_on_fail=False,
        )
