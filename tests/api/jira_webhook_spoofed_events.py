"""
* @file     ${tests/api/jira_webhook_spoofed_events.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that refused deliveries leave no successful sync event.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests that refused deliveries leave no successful sync event.
"""

from tests.bloom_test_base import BloomTestCase


class JiraWebhookSpoofedEventsBase(BloomTestCase):

    def bud_refused_deliveries_log_no_success(self):
        successes = [
            e
            for e in self.bloom.bloom_list_defect_events() + self.bloom.bloom_list_change_events()
            if e.success
        ]
        self.print_variables({"successful events": len(successes)})
        self.assertEqual(
            len(successes), 0, msg=self.parameters.MSG_NO_SPOOFED_EVENTS, abort_on_fail=False
        )
