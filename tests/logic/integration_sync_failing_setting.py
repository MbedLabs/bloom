"""
* @file     ${tests/logic/integration_sync_failing_setting.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a sync pass in which one integration fails.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of a failing integration among others.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncFailingSettingBase(BloomTestCase):

    def bud_only_the_other_setting_is_synced(self):
        self.print_variables({"synced": self.tc_synced})
        self.assertEqual(
            self.tc_synced,
            [self.tc_other_setting_id],
            msg=self.parameters.MSG_OTHER_SETTING_SYNCED,
            abort_on_fail=False,
        )

    def bud_failing_setting_records_its_error(self):
        error = self.bloom.bloom_get_setting(self.tc_failing_setting_id).sync_error
        self.print_variables({"error": error})
        self.assertEqual(
            error,
            self.parameters.SYNC_FAILED.format(text=self.parameters.FAILURE_TEXT),
            msg=self.parameters.MSG_FAILURE_RECORDED,
            abort_on_fail=False,
        )

    def bud_other_setting_is_synced_at_now(self):
        synced_at = self.bloom.bloom_get_setting(self.tc_other_setting_id).synced_at
        self.print_variables({"synced at": synced_at})
        self.assertEqual(
            synced_at,
            self.parameters.NOW,
            msg=self.parameters.MSG_OTHER_STAMPED,
            abort_on_fail=False,
        )
