"""
* @file     ${tests/logic/testrail.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the TestRail readers of XML suites and CSV exports.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the TestRail readers.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class TestrailBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_an_xml_case_keeps_its_fields(self):
        (cold, _), _ = self.bloom.bloom_parse_testrail("xml", self.parameters.TRL_SUITE_XML)
        self.assertEqual(
            (
                cold.case_id,
                cold.title,
                cold.sections,
                cold.case_type,
                cold.priority,
                cold.estimate,
                cold.references,
            ),
            ("C7", "Cold boot", ["Boot"], "Functional", "High", "5m", ["PRJ-REQ-001", "JIRA-9"]),
            msg=self.parameters.MSG_TRL_COLD,
            abort_on_fail=False,
        )
        self.assertEqual(
            (self.bloom.bloom_testrail_rows(cold), [r["id"] for r in cold.rows]),
            (self.parameters.TRL_COLD_ROWS, ["row-1", "row-2", "row-3", "row-4"]),
            msg=self.parameters.MSG_TRL_COLD_ROWS,
            abort_on_fail=False,
        )

    def bud_a_text_template_case_keeps_its_nested_section(self):
        (_, warm), _ = self.bloom.bloom_parse_testrail("xml", self.parameters.TRL_SUITE_XML)
        self.assertEqual(
            (warm.case_id, warm.sections, self.bloom.bloom_testrail_rows(warm)),
            ("C8", ["Boot", "Warm"], [("step", "Reset the board", "Banner within budget")]),
            msg=self.parameters.MSG_TRL_WARM,
            abort_on_fail=False,
        )

    def bud_unreadable_xml_is_refused(self):
        for what, data, phrase in self.parameters.TRL_BAD_XML:
            _, refusal = self.bloom.bloom_parse_testrail("xml", data)
            self.assertIn(
                phrase,
                refusal or "",
                msg=self.parameters.MSG_TRL_XML_REFUSED.format(what=what, phrase=phrase),
                abort_on_fail=False,
            )

    def bud_the_xml_import_limits_are_enforced(self):
        for limit, overrides, phrase in self.parameters.TRL_LIMITS:
            _, refusal = self.bloom.bloom_parse_testrail(
                "xml", self.parameters.TRL_SUITE_XML, **overrides
            )
            self.assertIn(
                phrase,
                refusal or "",
                msg=self.parameters.MSG_TRL_LIMIT.format(limit=limit),
                abort_on_fail=False,
            )

    def bud_case_ids_are_normalised(self):
        given, expected = self.parameters.TRL_CASE_IDS
        self.assertEqual(
            self.bloom.bloom_normalize_case_ids(given),
            expected,
            msg=self.parameters.MSG_TRL_CASE_IDS,
            abort_on_fail=False,
        )

    def bud_csv_rows_group_by_case_id(self):
        (cold, soak), _ = self.bloom.bloom_parse_testrail("csv", self.parameters.TRL_SEPARATED_CSV)
        self.assertEqual(
            (
                (cold.case_id, cold.title, cold.sections, cold.references),
                self.bloom.bloom_testrail_rows(cold),
                self.bloom.bloom_testrail_rows(soak),
            ),
            (
                ("C7", "Cold boot", ["Firmware", "Boot"], ["PRJ-REQ-001", "JIRA-9"]),
                self.parameters.TRL_CSV_COLD_ROWS,
                self.parameters.TRL_SOAK_ROWS,
            ),
            msg=self.parameters.MSG_TRL_CSV,
            abort_on_fail=False,
        )

    def bud_a_csv_text_template_case_has_one_step(self):
        (case,), _ = self.bloom.bloom_parse_testrail("csv", self.parameters.TRL_TEXT_CSV)
        self.assertEqual(
            (self.bloom.bloom_testrail_rows(case), case.case_id, case.sections),
            ([("step", "Reset the board", "Banner")], "", []),
            msg=self.parameters.MSG_TRL_CSV_TEXT,
            abort_on_fail=False,
        )

    def bud_a_csv_reads_through_a_column_mapping(self):
        (case,), _ = self.bloom.bloom_parse_testrail(
            "csv", self.parameters.TRL_MAPPED_CSV, self.parameters.TRL_MAPPING
        )
        self.assertEqual(
            (case.title, self.bloom.bloom_testrail_rows(case)),
            ("Cold boot", [("step", "Close relay", "Closed")]),
            msg=self.parameters.MSG_TRL_MAPPING,
            abort_on_fail=False,
        )

    def bud_unreadable_csv_is_refused(self):
        for what, data, mapping, phrase in self.parameters.TRL_BAD_CSV:
            _, refusal = self.bloom.bloom_parse_testrail("csv", data, mapping)
            self.assertIn(
                phrase,
                refusal or "",
                msg=self.parameters.MSG_TRL_CSV_REFUSED.format(what=what, phrase=phrase),
                abort_on_fail=False,
            )

    def bud_the_header_and_step_columns_are_detected(self):
        header, detected = self.bloom.bloom_testrail_header(self.parameters.TRL_SEPARATED_CSV)
        self.print_variables({"detected": detected})
        self.assertEqual(
            (
                header[0],
                detected["title"],
                detected["step"],
                detected["step_expected"],
                "steps" in detected,
            ),
            ("ID", "Title", "Steps (Step)", "Steps (Expected Result)", False),
            msg=self.parameters.MSG_TRL_COLUMNS,
            abort_on_fail=False,
        )

    def bud_a_csv_with_too_many_rows_is_refused(self):
        _, refusal = self.bloom.bloom_parse_testrail(
            "csv", self.parameters.TRL_SEPARATED_CSV, REQIF_MAX_RELATIONS=1
        )
        self.assertIn(
            "more rows", refusal or "", msg=self.parameters.MSG_TRL_ROW_LIMIT, abort_on_fail=False
        )

    def bud_a_new_case_model_has_no_rows(self):
        self.assertEqual(
            self.bloom.bloom_new_testrail_case("C1", "t").rows,
            [],
            msg=self.parameters.MSG_TRL_MODEL,
            abort_on_fail=False,
        )
