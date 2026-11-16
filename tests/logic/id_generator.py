"""
* @file     ${tests/logic/id_generator.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the shared document id generator.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the id generator.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IdGeneratorBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_the_next_id_follows_the_highest_existing_one(self):
        for case, existing, type_code, expected in self.parameters.IDG_CASES:
            self.assertEqual(
                self.bloom.bloom_compute_next_id(existing, "PRJ", type_code),
                (expected, None),
                msg=self.parameters.MSG_IDG_NEXT.format(case=case, expected=expected),
                abort_on_fail=False,
            )

    def bud_every_type_code_starts_at_001(self):
        for type_code in self.parameters.IDG_TYPE_CODES:
            self.assertEqual(
                self.bloom.bloom_compute_next_id([], "PRJ", type_code),
                (f"PRJ-{type_code}-001", None),
                msg=self.parameters.MSG_IDG_TYPE.format(type_code=type_code),
                abort_on_fail=False,
            )

    def bud_existing_ids_widen_when_999_is_passed(self):
        existing, expected = self.parameters.IDG_WIDEN
        self.assertEqual(
            self.bloom.bloom_widened_ids(existing, "PRJ", "REQ", 4),
            expected,
            msg=self.parameters.MSG_IDG_WIDEN,
            abort_on_fail=False,
        )

    def bud_widening_leaves_other_projects_and_types_alone(self):
        existing, expected = self.parameters.IDG_WIDEN_OTHERS
        self.assertEqual(
            self.bloom.bloom_widened_ids(existing, "PRJ", "REQ", 4),
            expected,
            msg=self.parameters.MSG_IDG_WIDEN_OTHERS,
            abort_on_fail=False,
        )

    def bud_the_id_pattern_accepts_three_and_four_digits(self):
        self.assertEqual(
            (
                self.bloom.bloom_id_pattern_matches("PRJ-REQ-0001"),
                self.bloom.bloom_id_pattern_matches("PRJ-REQ-001"),
            ),
            (True, True),
            msg=self.parameters.MSG_IDG_PATTERN,
            abort_on_fail=False,
        )

    def bud_a_project_prefix_that_is_not_three_letters_is_refused(self):
        self.assertIn(
            "exactly three uppercase letters",
            self.bloom.bloom_id_refusal([], "BLOOM", "REQ") or "",
            msg=self.parameters.MSG_IDG_PREFIX,
            abort_on_fail=False,
        )

    def bud_an_unsupported_type_code_is_refused(self):
        self.assertIn(
            "Unsupported document type code",
            self.bloom.bloom_id_refusal([], "PRJ", "BUG") or "",
            msg=self.parameters.MSG_IDG_TYPE_CODE,
            abort_on_fail=False,
        )

    def bud_a_supplied_id_is_normalized(self):
        self.assertEqual(
            self.bloom.bloom_normalize_doc_id(" prj-req-001 ", expected_type_code="REQ"),
            ("PRJ-REQ-001", None),
            msg=self.parameters.MSG_IDG_NORMALIZE,
            abort_on_fail=False,
        )

    def bud_a_supplied_id_of_another_project_is_refused(self):
        _, refusal = self.bloom.bloom_normalize_doc_id(
            "ABC-REQ-001", expected_type_code="REQ", expected_project_prefix="PRJ"
        )
        self.assertIn(
            "ID project prefix must be PRJ",
            refusal or "",
            msg=self.parameters.MSG_IDG_WRONG_PROJECT,
            abort_on_fail=False,
        )
