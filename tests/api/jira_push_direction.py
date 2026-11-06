"""
* @file     ${tests/api/jira_push_direction.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests when Bloom pushes edits of linked records to Jira.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests when Bloom pushes edits of linked records to Jira.
"""

from tests.bloom_test_base import BloomTestCase


class JiraPushDirectionBase(BloomTestCase):

    def bud_no_push_from_jira_to_bloom(self):
        self.print_variables({"pushed": self.tc_before})
        self.assertEqual(
            self.tc_before, [], msg=self.parameters.MSG_NO_PUSH_JIRA_TO_BLOOM, abort_on_fail=False
        )

    def bud_push_when_direction_includes_bloom_to_jira(self):
        self.print_variables({"pushed": self.tc_pushed})
        self.assertEqual(
            self.tc_pushed,
            [self.tc_env.defect_id, self.tc_env.change_id],
            msg=self.parameters.MSG_PUSH_BOTH,
            abort_on_fail=False,
        )
