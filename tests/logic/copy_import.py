"""
* @file     ${tests/logic/copy_import.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests copying requirements and test cases from one project into another.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the copy import.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class CopyImportBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_requirements_are_copied_as_drafts_after_the_highest_id(self):
        self.bloom.bloom_new_database()
        source, target = self.bloom.bloom_seed_copy_projects()
        values = self.parameters
        result = self.bloom.bloom_copy_docs("REQ", source, target, [values.CPY_MISSING_ID])
        self.print_variables(
            {
                "imported, skipped, new ids, errors": (
                    result.imported,
                    result.skipped,
                    result.new_ids,
                    result.errors,
                )
            }
        )
        self.assertEqual(
            (result.imported, result.skipped, result.new_ids, result.errors),
            (
                1,
                1,
                [values.CPY_COPIED_REQ],
                [f"Requirement {values.CPY_MISSING_ID} not found in source project"],
            ),
            msg=values.MSG_CPY_COUNTS,
            abort_on_fail=False,
        )
        copy = self.bloom.bloom_requirement_by_ref(values.CPY_COPIED_REQ)
        self.assertEqual(
            (copy.title, copy.description, copy.priority, copy.req_type, copy.req_origin),
            ("Boot", "Boots fast", "High", "functional", "customer"),
            msg=values.MSG_CPY_FIELDS,
            abort_on_fail=False,
        )
        self.assertEqual(
            (copy.status, copy.source_ref, copy.source_project_id),
            ("Draft", "PRJ-REQ-001", source),
            msg=values.MSG_CPY_SOURCE,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.bloom.bloom_next_number(target, "ABC", "REQ"),
            9,
            msg=values.MSG_CPY_NEXT,
            abort_on_fail=False,
        )

    def bud_test_cases_keep_their_steps_and_preconditions(self):
        self.bloom.bloom_new_database()
        source, target = self.bloom.bloom_seed_copy_projects()
        values = self.parameters
        result = self.bloom.bloom_copy_docs("TC", source, target)
        copy = self.bloom.bloom_test_case_by_ref(values.CPY_COPIED_TC)
        self.assertEqual(
            (result.new_ids, copy.preconditions, copy.steps, copy.status, copy.source_ref),
            ([values.CPY_COPIED_TC], "Powered", [{"action": "Power on"}], "Draft", "PRJ-TC-001"),
            msg=values.MSG_CPY_TEST_CASE,
            abort_on_fail=False,
        )
