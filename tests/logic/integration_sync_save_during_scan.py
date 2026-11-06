"""
* @file     ${tests/logic/integration_sync_save_during_scan.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a save of the integration while its full scan runs.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of a save during a scan.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncSaveDuringScanBase(BloomTestCase):

    def bud_save_during_a_full_scan_keeps_the_rescan(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        found = (setting.synced_at, setting.sync_full_scan)
        self.print_variables({"synced at, full scan": found})
        self.assertEqual(
            found,
            (self.parameters.NOW, True),
            msg=self.parameters.MSG_SAVE_DURING_SCAN,
            abort_on_fail=False,
        )
