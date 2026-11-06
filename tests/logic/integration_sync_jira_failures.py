"""
* @file     ${tests/logic/integration_sync_jira_failures.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests Jira sync runs that fail on the account or the connection.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of failed Jira sync runs.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncJiraFailuresBase(BloomTestCase):

    def bud_refused_account_is_the_run_error(self):
        self.print_variables({"error": self.tc_refused.sync_error})
        self.assertTrue(
            (self.tc_refused.sync_error or "").startswith(self.parameters.JIRA_REFUSED_ACCOUNT),
            msg=self.parameters.MSG_REFUSED_ACCOUNT,
            abort_on_fail=False,
        )

    def bud_refused_run_keeps_the_last_success_and_counts(self):
        found = (
            self.tc_refused.synced_at,
            self.tc_refused.sync_created,
            self.tc_refused.sync_updated,
        )
        self.print_variables({"synced at, created, updated": found})
        self.assertEqual(
            found,
            (self.tc_before, *self.parameters.PREVIOUS_COUNTS),
            msg=self.parameters.MSG_LAST_SUCCESS_KEPT,
            abort_on_fail=False,
        )

    def bud_unreachable_jira_is_the_run_error(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.print_variables({"error": setting.sync_error})
        self.assertTrue(
            (setting.sync_error or "").startswith(self.parameters.JIRA_UNREACHABLE),
            msg=self.parameters.MSG_UNREACHABLE,
            abort_on_fail=False,
        )

    def bud_unreachable_run_keeps_the_last_success_and_scan_state(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.print_variables({"synced at": setting.synced_at, "full scan": setting.sync_full_scan})
        self.assertEqual(
            (setting.synced_at, setting.sync_full_scan),
            (self.tc_before, False),
            msg=self.parameters.MSG_UNREACHABLE_KEEPS,
            abort_on_fail=False,
        )
