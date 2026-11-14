"""
* @file     ${tests/logic/integration_sync_unreadable_repository.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a GitHub sync with one unreadable repository.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of an unreadable repository.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncUnreadableRepositoryBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_readable_repository_is_still_synced(self):
        self.print_variables({"readable defect": self.tc_readable_status})
        self.assertEqual(
            self.tc_readable_status,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_READABLE_SYNCED,
            abort_on_fail=False,
        )

    def bud_run_succeeds_with_a_warning_naming_the_repository(self):
        found = (
            self.tc_first_run.synced_at,
            self.tc_first_run.sync_warning,
            self.tc_first_run.sync_error,
        )
        self.print_variables({"synced at, warning, error": found})
        self.assertEqual(
            found,
            (
                self.parameters.NOW,
                self.parameters.GITHUB_WARNING.format(repo=self.parameters.OTHER_REPO),
                None,
            ),
            msg=self.parameters.MSG_UNREADABLE_WARNING,
            abort_on_fail=False,
        )

    def bud_warning_clears_once_the_repository_reads_again(self):
        warning = self.bloom.bloom_get_setting(self.tc_setting_id).sync_warning
        self.print_variables({"warning after the next run": warning})
        self.assertEqual(
            (warning,), (None,), msg=self.parameters.MSG_WARNING_CLEARED, abort_on_fail=False
        )
