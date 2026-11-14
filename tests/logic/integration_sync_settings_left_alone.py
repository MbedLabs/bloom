"""
* @file     ${tests/logic/integration_sync_settings_left_alone.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which integrations a sync pass leaves alone.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of integrations the sync skips.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncSettingsLeftAloneBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_no_setting_is_synced(self):
        self.print_variables({"synced": self.tc_synced})
        self.assertEqual(
            self.tc_synced, [], msg=self.parameters.MSG_NOTHING_SYNCED, abort_on_fail=False
        )

    def bud_no_tracker_is_called(self):
        self.print_variables({"calls": self.bloom.site.calls})
        self.assertEqual(
            len(self.bloom.site.calls),
            0,
            msg=self.parameters.MSG_NOTHING_CALLED,
            abort_on_fail=False,
        )

    def bud_setting_checked_recently_keeps_its_check_time(self):
        checked = self.bloom.bloom_get_setting(self.tc_recent_id).sync_checked_at
        self.print_variables({"checked at": checked})
        self.assertEqual(
            checked,
            self.parameters.NOW - self.parameters.RECENT_CHECK,
            msg=self.parameters.MSG_NOT_DUE_UNTOUCHED,
            abort_on_fail=False,
        )

    def bud_disabled_setting_records_nothing(self):
        setting = self.bloom.bloom_get_setting(self.tc_disabled_id)
        found = (setting.sync_checked_at, setting.sync_error)
        self.print_variables({"checked at, error": found})
        self.assertEqual(
            found, (None, None), msg=self.parameters.MSG_SKIPPED_UNTOUCHED, abort_on_fail=False
        )

    def bud_tokenless_setting_records_nothing(self):
        setting = self.bloom.bloom_get_setting(self.tc_tokenless_id)
        found = (setting.sync_checked_at, setting.sync_error)
        self.print_variables({"checked at, error": found})
        self.assertEqual(
            found, (None, None), msg=self.parameters.MSG_SKIPPED_UNTOUCHED, abort_on_fail=False
        )
