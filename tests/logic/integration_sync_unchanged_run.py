"""
* @file     ${tests/logic/integration_sync_unchanged_run.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a Jira sync run that finds nothing new to change.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of an unchanged Jira sync run.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncUnchangedRunBase(BloomTestCase):

    def bud_first_run_logs_the_follow_up(self):
        self.print_variables({"events after the first run": self.tc_first_events})
        self.assertEqual(
            self.tc_first_events,
            1,
            msg=self.parameters.MSG_UNCHANGED_FIRST_EVENT,
            abort_on_fail=False,
        )

    def bud_unchanged_run_logs_no_event(self):
        count = len(self.bloom.bloom_list_defect_events())
        self.print_variables({"events after the second run": count})
        self.assertEqual(count, 1, msg=self.parameters.MSG_UNCHANGED_NO_EVENT, abort_on_fail=False)

    def bud_unchanged_run_leaves_the_setting_alone(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.print_variables({"updated at": setting.updated_at, "updated": setting.sync_updated})
        self.assertEqual(
            (setting.updated_at, setting.sync_updated),
            (self.tc_updated_at, 0),
            msg=self.parameters.MSG_UNCHANGED_SETTING,
            abort_on_fail=False,
        )
