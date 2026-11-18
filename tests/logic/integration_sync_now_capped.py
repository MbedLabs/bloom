"""
* @file     ${tests/logic/integration_sync_now_capped.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests Sync now with a capped full search.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of a capped Sync now.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncNowCappedBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_capped_sync_now_keeps_the_full_scan_from_the_last_created_issue(self):
        setting = self.bloom.bloom_get_setting(self.setting_id)
        first_state = (setting.sync_full_scan, setting.sync_scan_from)
        self.print_variables({"full scan, scan from": first_state})
        self.assertEqual(
            first_state,
            (True, self.parameters.FIRST_CREATED),
            msg=self.parameters.MSG_SYNC_NOW_CAPPED,
            abort_on_fail=False,
        )

    def bud_next_sync_now_continues_by_creation_time(self):
        self.bloom.bloom_sync_now(self.setting_id, self.parameters.OTHER_ADMIN_EMAIL)
        next_creation = [q for q in self.bloom.site.jql if self.parameters.CREATION_MARK in q][1]
        self.print_variables({"next creation search": next_creation})
        self.assertIn(
            member=self.parameters.CREATED_WINDOW,
            container=next_creation,
            msg=self.parameters.MSG_NEXT_SEARCH_BY_CREATION,
            abort_on_fail=False,
        )
