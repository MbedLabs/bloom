"""
* @file     ${tests/api/jira_webhook_closes_change.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a signed webhook that closes a linked change request.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests a signed webhook that closes a linked change request.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraWebhookClosesChangeBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_signed_update_answers_for_the_change_request(self):
        found = (self.tc_response.status_code, self.tc_response.json().get("target"))
        self.print_variables({"status, target": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.parameters.TARGET_CHANGE),
            msg=self.parameters.MSG_CHANGE_TARGET,
            abort_on_fail=False,
        )

    def bud_linked_change_request_is_closed(self):
        status = self.bloom.bloom_get_change(self.tc_env.change_id).status
        self.print_variables({"change request": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_CHANGE_CLOSED_BY_WEBHOOK,
            abort_on_fail=False,
        )

    def bud_same_delivery_again_is_a_duplicate(self):
        found = (self.tc_repeat.status_code, self.tc_repeat.json().get("status"))
        self.print_variables({"status, answer": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.parameters.ANSWER_DUPLICATE),
            msg=self.parameters.MSG_REPEAT_IS_DUPLICATE,
            abort_on_fail=False,
        )

    def bud_change_request_logs_one_successful_sync(self):
        successes = [e for e in self.bloom.bloom_list_change_events() if e.success]
        self.print_variables({"successful events": len(successes)})
        self.assertEqual(
            len(successes), 1, msg=self.parameters.MSG_ONE_SUCCESS_EVENT, abort_on_fail=False
        )
