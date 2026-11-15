"""
* @file     ${tests/logic/next_doc_id.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the next document id the create screen previews.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the next document id.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class NextDocIdBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_empty_project_starts_at_its_first_id(self):
        self.print_variables({"preview": self.tc_empty})
        self.assertEqual(
            self.tc_empty,
            (self.parameters.NEXT_ID_FIRST, None),
            msg=self.parameters.MSG_NEXT_ID_EMPTY,
            abort_on_fail=False,
        )

    def bud_preview_advances_past_the_taken_id(self):
        self.print_variables(
            {"taken": self.parameters.NEXT_ID_TAKEN_IDS, "preview": self.tc_after_taken}
        )
        self.assertEqual(
            self.tc_after_taken,
            (self.parameters.NEXT_ID_AFTER_TAKEN, None),
            msg=self.parameters.MSG_NEXT_ID_TAKEN,
            abort_on_fail=False,
        )

    def bud_preview_follows_the_highest_number(self):
        self.print_variables(
            {"taken": self.parameters.NEXT_ID_GAP_IDS, "preview": self.tc_after_gap}
        )
        self.assertEqual(
            self.tc_after_gap,
            (self.parameters.NEXT_ID_AFTER_HIGH, None),
            msg=self.parameters.MSG_NEXT_ID_HIGHEST,
            abort_on_fail=False,
        )

    def bud_preview_ignores_other_types_and_projects(self):
        self.print_variables(
            {"taken": self.parameters.NEXT_ID_MIXED_IDS, "preview": self.tc_among_others}
        )
        self.assertEqual(
            self.tc_among_others,
            (self.parameters.NEXT_ID_AFTER_LOW, None),
            msg=self.parameters.MSG_NEXT_ID_OTHERS,
            abort_on_fail=False,
        )

    def bud_unsupported_type_is_refused(self):
        self.print_variables(
            {"type": self.parameters.NEXT_ID_UNSUPPORTED_TYPE, "answer": self.tc_unsupported}
        )
        self.assertEqual(
            self.tc_unsupported,
            (None, self.parameters.NEXT_ID_ERROR),
            msg=self.parameters.MSG_NEXT_ID_UNSUPPORTED,
            abort_on_fail=False,
        )

    def bud_next_id_has_its_own_route(self):
        self.print_variables({"route": self.parameters.NEXT_ID_ROUTE})
        self.assertIn(
            self.parameters.NEXT_ID_ROUTE,
            self.tc_routes,
            msg=self.parameters.MSG_NEXT_ID_ROUTE,
            abort_on_fail=False,
        )
