"""
* @file     ${tests/logic/integration_sync_creation_off.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the scheduled Jira sync of an integration that creates no defects.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the Jira sync with creation off.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncCreationOffBase(BloomTestCase):

    def bud_no_creation_search_runs(self):
        creation = [q for q in self.bloom.site.jql if self.parameters.CREATION_MARK in q]
        self.print_variables({"creation search": creation})
        self.assertEqual(
            creation, [], msg=self.parameters.MSG_NO_CREATION_SEARCH, abort_on_fail=False
        )

    def bud_only_the_linked_defect_exists(self):
        count = self.bloom.bloom_count_defects()
        self.print_variables({"defects": count})
        self.assertEqual(count, 1, msg=self.parameters.MSG_ONLY_LINKED, abort_on_fail=False)

    def bud_linked_defect_follows_its_closed_issue(self):
        status = self.bloom.bloom_get_defect(self.tc_linked_defect_id).status
        self.print_variables({"linked defect": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_LINKED_CLOSED,
            abort_on_fail=False,
        )
