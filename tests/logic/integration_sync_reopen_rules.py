"""
* @file     ${tests/logic/integration_sync_reopen_rules.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests when an open GitHub issue reopens its defect.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the reopen rules.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncReopenRulesBase(BloomTestCase):

    def bud_open_issue_leaves_a_working_defect_in_progress(self):
        status = self.bloom.bloom_get_defect(self.tc_working_id).status
        self.print_variables({"working defect": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_IN_PROGRESS,
            msg=self.parameters.MSG_WORKING_KEPT,
            abort_on_fail=False,
        )

    def bud_issue_open_again_reopens_its_defect(self):
        defect = self.bloom.bloom_get_defect(self.tc_reopened_id)
        found = (defect.status, defect.closed_at, defect.external_issue_closed)
        self.print_variables({"status, closed at, issue closed": found})
        self.assertEqual(
            found,
            (self.parameters.DEFECT_OPEN, None, False),
            msg=self.parameters.MSG_REOPENED,
            abort_on_fail=False,
        )

    def bud_defect_closed_in_bloom_stays_closed(self):
        status = self.bloom.bloom_get_defect(self.tc_closed_in_bloom_id).status
        self.print_variables({"defect closed in Bloom": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_CLOSED_IN_BLOOM_KEPT,
            abort_on_fail=False,
        )
