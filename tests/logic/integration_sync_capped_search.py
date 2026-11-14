"""
* @file     ${tests/logic/integration_sync_capped_search.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a Jira sync whose searches are capped.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of a capped Jira search.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncCappedSearchBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_capped_run_keeps_the_full_scan(self):
        self.print_variables({"full scan": self.tc_first_run.sync_full_scan})
        self.assertEqual(
            self.tc_first_run.sync_full_scan,
            True,
            msg=self.parameters.MSG_CAPPED_KEEPS_FULL_SCAN,
            abort_on_fail=False,
        )

    def bud_capped_run_continues_from_the_last_created_issue_in_utc(self):
        self.print_variables({"scan from": self.tc_first_run.sync_scan_from})
        self.assertEqual(
            self.tc_first_run.sync_scan_from,
            self.parameters.SECOND_CREATED,
            msg=self.parameters.MSG_CAPPED_CONTINUES_FROM,
            abort_on_fail=False,
        )

    def bud_capped_run_is_synced_up_to_the_last_update_in_utc(self):
        self.print_variables({"synced at": self.tc_first_run.synced_at})
        self.assertEqual(
            self.tc_first_run.synced_at,
            self.tc_second_updated,
            msg=self.parameters.MSG_CAPPED_SYNCED_UP_TO,
            abort_on_fail=False,
        )

    def bud_next_creation_search_goes_by_creation_time(self):
        self.print_variables({"next creation search": self.tc_next_creation})
        self.assertIn(
            member=self.parameters.CREATED_WINDOW,
            container=self.tc_next_creation,
            msg=self.parameters.MSG_NEXT_SEARCH_BY_CREATION,
            abort_on_fail=False,
        )

    def bud_next_creation_search_ignores_update_time(self):
        self.print_variables({"next creation search": self.tc_next_creation})
        self.assertNotIn(
            member=self.parameters.UPDATED_WINDOW,
            container=self.tc_next_creation,
            msg=self.parameters.MSG_NEXT_SEARCH_NOT_BY_UPDATE,
            abort_on_fail=False,
        )
