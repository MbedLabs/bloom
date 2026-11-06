"""
* @file     ${tests/logic/integration_sync_save_rescan.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that saving an integration asks for a new full scan.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the rescan after a save.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncSaveRescanBase(BloomTestCase):

    def bud_first_run_clears_the_full_scan(self):
        self.print_variables({"full scan after the run": self.tc_after_run})
        self.assertEqual(
            self.tc_after_run, False, msg=self.parameters.MSG_FULL_SCAN_CLEARED, abort_on_fail=False
        )

    def bud_save_asks_for_a_full_scan_from_the_start(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        found = (setting.sync_full_scan, setting.sync_scan_from)
        self.print_variables({"full scan, scan from": found})
        self.assertEqual(
            found, (True, None), msg=self.parameters.MSG_SAVE_RESCAN, abort_on_fail=False
        )
