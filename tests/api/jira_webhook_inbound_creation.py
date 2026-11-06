"""
* @file     ${tests/api/jira_webhook_inbound_creation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests defects created from Jira deliveries.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests defects created from Jira deliveries.
"""

from tests.bloom_test_base import BloomTestCase


class JiraWebhookInboundCreationBase(BloomTestCase):

    def bud_unmatched_issue_creates_a_defect(self):
        found = (
            self.tc_response.status_code,
            self.tc_response.json().get("status"),
            self.tc_response.json().get("target"),
        )
        self.print_variables({"status, answer, target": found})
        self.assertEqual(
            found,
            (
                self.parameters.STATUS_OK,
                self.parameters.ANSWER_CREATED,
                self.parameters.TARGET_DEFECT,
            ),
            msg=self.parameters.MSG_INBOUND_CREATED,
            abort_on_fail=False,
        )

    def bud_created_defect_takes_the_summary_and_is_open(self):
        found = [
            (d.title, d.status)
            for d in self.bloom.bloom_list_defects_linked_to(self.parameters.WEBHOOK_NEW_NUMBER)
        ]
        self.print_variables({"created": found})
        self.assertEqual(
            found,
            [(self.parameters.NEW_SUMMARY, self.parameters.DEFECT_OPEN)],
            msg=self.parameters.MSG_INBOUND_CONTENT,
            abort_on_fail=False,
        )

    def bud_replayed_create_makes_no_second_defect(self):
        found = (
            self.tc_replay.json().get("status"),
            len(self.bloom.bloom_list_defects_linked_to(self.parameters.WEBHOOK_NEW_NUMBER)),
        )
        self.print_variables({"answer, defects": found})
        self.assertEqual(
            found,
            (self.parameters.ANSWER_DUPLICATE, 1),
            msg=self.parameters.MSG_INBOUND_IDEMPOTENT,
            abort_on_fail=False,
        )
