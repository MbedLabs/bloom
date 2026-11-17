"""
* @file     ${tests/pg/id_widening.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the stored ids when a project's requirement ids pass 999.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the id widening.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class IdWideningBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_id_after_999_is_1000(self):
        next_id = self.bloom.bloom_next_requirement_id(
            self.at_boundary, self.parameters.WIDENING_PREFIXES[0]
        )
        self.print_variables({"next id": next_id})
        self.assertEqual(
            next_id,
            self.parameters.WIDENING_NEXT_AT_BOUNDARY,
            msg=self.parameters.MSG_WIDENING_NEXT,
            abort_on_fail=False,
        )

    def bud_stored_ids_are_rewritten_with_four_digits(self):
        stored = self.bloom.bloom_list_requirement_ids(self.at_boundary)
        self.print_variables({"stored": stored})
        self.assertEqual(
            stored,
            self.parameters.WIDENING_WIDENED,
            msg=self.parameters.MSG_WIDENING_STORED,
            abort_on_fail=False,
        )

    def bud_below_999_the_next_id_keeps_three_digits(self):
        next_id = self.bloom.bloom_next_requirement_id(
            self.below, self.parameters.WIDENING_PREFIXES[1]
        )
        self.print_variables({"next id": next_id})
        self.assertEqual(
            next_id,
            self.parameters.WIDENING_NEXT_BELOW,
            msg=self.parameters.MSG_WIDENING_BELOW_NEXT,
            abort_on_fail=False,
        )

    def bud_below_999_stored_ids_are_not_rewritten(self):
        stored = self.bloom.bloom_list_requirement_ids(self.below)
        self.print_variables({"stored": stored})
        self.assertEqual(
            stored,
            self.parameters.WIDENING_BELOW,
            msg=self.parameters.MSG_WIDENING_BELOW_STORED,
            abort_on_fail=False,
        )

    def bud_widening_leaves_the_test_case_id_alone(self):
        self.bloom.bloom_next_requirement_id(self.other_type, self.parameters.WIDENING_PREFIXES[2])
        ids = self.bloom.bloom_list_test_case_ids()
        self.print_variables({"test case ids": ids})
        self.assertEqual(
            ids,
            [self.parameters.WIDENING_TEST_CASE],
            msg=self.parameters.MSG_WIDENING_OTHER_TYPE,
            abort_on_fail=False,
        )
