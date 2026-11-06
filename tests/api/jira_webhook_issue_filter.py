"""
* @file     ${tests/api/jira_webhook_issue_filter.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which Jira issues a mapped project takes in.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests which Jira issues a mapped project takes in.
"""

from tests.bloom_test_base import BloomTestCase


class JiraWebhookIssueFilterBase(BloomTestCase):

    def bud_task_is_ignored(self):
        self.print_variables({"answer": self.tc_task.json()})
        self.assertEqual(
            self.tc_task.json().get("status"),
            self.parameters.ANSWER_IGNORED,
            msg=self.parameters.MSG_TASK_IGNORED,
            abort_on_fail=False,
        )

    def bud_unlabelled_issue_is_ignored(self):
        self.print_variables({"answer": self.tc_unlabelled.json()})
        self.assertEqual(
            self.tc_unlabelled.json(),
            self.parameters.NOT_TAKEN_IN,
            msg=self.parameters.MSG_UNLABELLED_IGNORED,
            abort_on_fail=False,
        )

    def bud_labelled_issue_creates_a_defect_without_reporter(self):
        created = self.bloom.bloom_list_defects_linked_to(self.parameters.FILTER_NUMBERS[2])
        found = (self.tc_labelled.json().get("status"), [d.reporter_id for d in created])
        self.print_variables({"answer, reporters": found})
        self.assertEqual(
            found,
            (self.parameters.ANSWER_CREATED, [None]),
            msg=self.parameters.MSG_LABELLED_CREATED,
            abort_on_fail=False,
        )

    def bud_deletion_of_an_unknown_issue_is_ignored(self):
        self.print_variables({"answer": self.tc_gone.json()})
        self.assertEqual(
            self.tc_gone.json().get("status"),
            self.parameters.ANSWER_IGNORED,
            msg=self.parameters.MSG_UNKNOWN_DELETE_IGNORED,
            abort_on_fail=False,
        )
