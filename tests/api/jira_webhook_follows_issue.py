"""
* @file     ${tests/api/jira_webhook_follows_issue.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests how a linked defect follows its Jira issue.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests how a linked defect follows its Jira issue.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraWebhookFollowsIssueBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_edit_is_processed(self):
        self.print_variables({"answer": self.tc_edit.json()})
        self.assertEqual(
            self.tc_edit.json().get("status"),
            self.parameters.ANSWER_PROCESSED,
            msg=self.parameters.MSG_FOLLOWS_ISSUE,
            abort_on_fail=False,
        )

    def bud_defect_takes_the_issue_fields_and_stays_open(self):
        defect = self.tc_after_edit
        found = (
            defect.title,
            defect.description,
            defect.priority,
            defect.status,
            defect.external_issue_url,
        )
        self.print_variables({"defect": found})
        self.assertEqual(
            found,
            (
                self.parameters.CHANGED_TITLE,
                self.parameters.CHANGED_DESCRIPTION,
                self.parameters.BLOOM_PRIORITY,
                self.parameters.DEFECT_OPEN,
                f"{self.parameters.JIRA_URL}/browse/{self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER)}",
            ),
            msg=self.parameters.MSG_FOLLOWS_ISSUE,
            abort_on_fail=False,
        )

    def bud_resolution_closes_the_defect(self):
        defect = self.bloom.bloom_get_defect(self.tc_env.defect_id)
        found = (defect.status, defect.closed_at is not None)
        self.print_variables({"status, closed": found})
        self.assertEqual(
            found,
            (self.parameters.DEFECT_CLOSED, True),
            msg=self.parameters.MSG_RESOLUTION_CLOSES,
            abort_on_fail=False,
        )
