"""
* @file     ${tests/logic/integration_sync_linked_during_search.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a defect linked to a Jira issue while the sync searches Jira.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of a defect linked during the search.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncLinkedDuringSearchBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_defect_linked_during_the_search_is_not_created_twice(self):
        count = self.bloom.bloom_count_defects()
        self.print_variables({"defects": count})
        self.assertEqual(count, 1, msg=self.parameters.MSG_NOT_CREATED_TWICE, abort_on_fail=False)
