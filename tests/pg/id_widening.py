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
        self.print_variables({"next id": self.next_at_boundary})
        self.assertEqual(
            self.next_at_boundary,
            self.parameters.WIDENING_NEXT_AT_BOUNDARY,
            msg=self.parameters.MSG_WIDENING_NEXT,
            abort_on_fail=False,
        )

    def bud_stored_ids_are_rewritten_with_four_digits(self):
        self.print_variables({"stored": self.stored_at_boundary})
        self.assertEqual(
            self.stored_at_boundary,
            self.parameters.WIDENING_WIDENED,
            msg=self.parameters.MSG_WIDENING_STORED,
            abort_on_fail=False,
        )

    def bud_below_999_the_next_id_keeps_three_digits(self):
        self.print_variables({"next id": self.next_below})
        self.assertEqual(
            self.next_below,
            self.parameters.WIDENING_NEXT_BELOW,
            msg=self.parameters.MSG_WIDENING_BELOW_NEXT,
            abort_on_fail=False,
        )

    def bud_below_999_stored_ids_are_not_rewritten(self):
        self.print_variables({"stored": self.stored_below})
        self.assertEqual(
            self.stored_below,
            self.parameters.WIDENING_BELOW,
            msg=self.parameters.MSG_WIDENING_BELOW_STORED,
            abort_on_fail=False,
        )

    def bud_widening_leaves_the_test_case_id_alone(self):
        self.print_variables({"test case ids": self.test_case_ids})
        self.assertEqual(
            self.test_case_ids,
            [self.parameters.WIDENING_TEST_CASE],
            msg=self.parameters.MSG_WIDENING_OTHER_TYPE,
            abort_on_fail=False,
        )
