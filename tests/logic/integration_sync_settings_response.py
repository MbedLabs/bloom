"""
* @file     ${tests/logic/integration_sync_settings_response.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the sync state in the integration settings API answer.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the settings response.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncSettingsResponseBase(BloomTestCase):

    def bud_sync_times_are_given_in_utc(self):
        expected = self.parameters.NOW.strftime(self.parameters.API_TIME_FORMAT)
        found = (self.tc_response["synced_at"], self.tc_response["sync_checked_at"])
        self.print_variables({"synced at, checked at": found})
        self.assertEqual(
            found, (expected, expected), msg=self.parameters.MSG_RESPONSE_TIMES, abort_on_fail=False
        )

    def bud_warning_error_counts_and_own_rate_are_given(self):
        created, updated = self.parameters.PREVIOUS_COUNTS
        keys = ("sync_warning", "sync_error", "sync_created", "sync_updated", "auto_sync_minutes")
        found = tuple(self.tc_response[key] for key in keys)
        self.print_variables({"warning, error, created, updated, rate": found})
        self.assertEqual(
            found,
            (self.parameters.WARNING_TEXT, None, created, updated, self.parameters.SYNC_RATE),
            msg=self.parameters.MSG_RESPONSE_STATE,
            abort_on_fail=False,
        )
