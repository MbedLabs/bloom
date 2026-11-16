"""
* @file     ${tests/logic/import_test_cases.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests importing test cases from CSV and XML in the export format.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the test case import.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ImportTestCasesBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_a_csv_import_updates_the_existing_and_creates_a_new_test_case(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_import_case()
        values = self.parameters
        result = self.bloom.bloom_import_test_cases(project, "csv", values.ITC_UPDATE_CSV)
        self.assertEqual(
            (result.updated, result.created), (1, 1), msg=values.MSG_ITC_UPDATE, abort_on_fail=False
        )
        tc = self.bloom.bloom_test_case_by_ref("PRJ-TC-001")
        self.assertEqual(
            (
                tc.title,
                tc.status,
                [(s["row_type"], s["description"], s["expected_result"]) for s in tc.steps],
                len(self.bloom.bloom_list_test_cases()),
            ),
            ("Updated login", "Draft", [("step", "Open", "Form")], 2),
            msg=values.MSG_ITC_UPDATED,
            abort_on_fail=False,
        )

    def bud_a_csv_import_cannot_approve_test_cases(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_import_case()
        values = self.parameters
        result = self.bloom.bloom_import_test_cases(project, "csv", values.ITC_APPROVE_CSV)
        cases = [(c.tc_id, c.title, c.status) for c in self.bloom.bloom_list_test_cases()]
        self.print_variables({"cases": cases})
        self.assertEqual(
            ((result.updated, result.created, result.skipped), cases),
            ((0, 0, 2), [("PRJ-TC-001", "Verify login", "Draft")]),
            msg=values.MSG_ITC_NO_APPROVAL,
            abort_on_fail=False,
        )

    def bud_an_xml_import_creates_a_test_case(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_import_case()
        values = self.parameters
        result = self.bloom.bloom_import_test_cases(project, "xml", values.ITC_XML)
        tc = self.bloom.bloom_test_case_titled("From XML")
        self.assertEqual(
            (
                result.created,
                [(s["row_type"], s["description"], s["expected_result"]) for s in tc.steps],
                tc.tc_id.startswith("PRJ-TC-"),
            ),
            (1, [("step", "Click", "Opens")], True),
            msg=values.MSG_ITC_XML,
            abort_on_fail=False,
        )

    def bud_a_row_without_a_title_is_skipped(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_import_case()
        values = self.parameters
        result = self.bloom.bloom_import_test_cases(project, "csv", values.ITC_NO_TITLE_CSV)
        self.assertEqual(
            (result.skipped, result.created, result.errors),
            (1, 0, ["row 1: missing title"]),
            msg=values.MSG_ITC_NO_TITLE,
            abort_on_fail=False,
        )
