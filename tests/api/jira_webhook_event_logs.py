"""
* @file     ${tests/api/jira_webhook_event_logs.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests where sync events are logged.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests where sync events are logged.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraWebhookEventLogsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_events_land_in_their_own_logs(self):
        found = (
            [e.event_type for e in self.bloom.bloom_list_defect_events()],
            [e.event_type for e in self.bloom.bloom_list_change_events()],
        )
        self.print_variables({"defect events, change events": found})
        self.assertEqual(
            found,
            ([self.parameters.PROBE_DEFECT_EVENT], [self.parameters.PROBE_CHANGE_EVENT]),
            msg=self.parameters.MSG_EVENTS_ROUTED,
            abort_on_fail=False,
        )
