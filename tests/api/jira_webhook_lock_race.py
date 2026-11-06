"""
* @file     ${tests/api/jira_webhook_lock_race.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a create delivery whose issue is linked while it waits for the lock.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests a create delivery whose issue is linked while it waits for the lock.
"""

from tests.bloom_test_base import BloomTestCase


class JiraWebhookLockRaceBase(BloomTestCase):

    def bud_delivery_is_processed(self):
        found = (self.tc_response.status_code, self.tc_response.json().get("status"))
        self.print_variables({"status, answer": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.parameters.ANSWER_PROCESSED),
            msg=self.parameters.MSG_RACE_PROCESSED,
            abort_on_fail=False,
        )

    def bud_linked_defect_is_followed_not_doubled(self):
        titles = [
            d.title for d in self.bloom.bloom_list_defects_linked_to(self.parameters.RACE_NUMBER)
        ]
        self.print_variables({"titles": titles})
        self.assertEqual(
            titles,
            [self.parameters.NEW_SUMMARY],
            msg=self.parameters.MSG_RACE_NOT_DOUBLED,
            abort_on_fail=False,
        )
