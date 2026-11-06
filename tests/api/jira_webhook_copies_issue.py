"""
* @file     ${tests/api/jira_webhook_copies_issue.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what a defect created from a Jira issue copies.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests what a defect created from a Jira issue copies.
"""

from tests.bloom_test_base import BloomTestCase


class JiraWebhookCopiesIssueBase(BloomTestCase):

    def bud_issue_creates_a_defect(self):
        self.print_variables({"answer": self.tc_response.json()})
        self.assertEqual(
            self.tc_response.json().get("status"),
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
                self.tc_description,
                self.parameters.CRITICAL,
                self.parameters.CRITICAL,
                f"{self.parameters.JIRA_URL}/browse/{self.tc_key}",
                self.parameters.SOURCE_TC,
                self.tc_test_case_id,
                self.parameters.JIRA_TO_DO,
                self.tc_bot_id,
            ),
            msg=self.parameters.MSG_COPIES_ISSUE,
            abort_on_fail=False,
        )
