"""
* @file     ${tests/pg/integration_sync_race.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests Sync now and a scheduled run racing on one integration.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the sync race on PostgreSQL.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncRaceBase(BloomTestCase):

    def bud_both_runs_searched_before_either_wrote(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"creation searches": len(self.tc_searches)})
        self.assertEqual(
            len(self.tc_searches), 2, msg=self.parameters.MSG_BOTH_SEARCHED, abort_on_fail=False
        )

    def bud_one_defect_is_created_for_the_issue(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        count = self.bloom.bloom_count_defects()
        self.print_variables({"defects": count})
        self.assertEqual(count, 1, msg=self.parameters.MSG_RACE_ONE_DEFECT, abort_on_fail=False)
