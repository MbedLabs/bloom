"""
* @file     ${tests/logic/integration_sync_now_capped.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests Sync now with a capped full search.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of a capped Sync now.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncNowCappedBase(BloomTestCase):

    def bud_capped_sync_now_keeps_the_full_scan_from_the_last_created_issue(self):
        self.print_variables({"full scan, scan from": self.tc_first_state})
        self.assertEqual(
            self.tc_first_state,
            (True, self.parameters.FIRST_CREATED),
            msg=self.parameters.MSG_SYNC_NOW_CAPPED,
            abort_on_fail=False,
        )

    def bud_next_sync_now_continues_by_creation_time(self):
        self.print_variables({"next creation search": self.tc_next_creation})
        self.assertIn(
            member=self.parameters.CREATED_WINDOW,
            container=self.tc_next_creation,
            msg=self.parameters.MSG_NEXT_SEARCH_BY_CREATION,
            abort_on_fail=False,
        )
