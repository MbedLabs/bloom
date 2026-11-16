"""
* @file     ${tests/logic/export.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the requirements and traceability exports.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the requirements and traceability exports.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ExportBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_the_requirements_csv_holds_both_requirements(self):
        answer = self.bloom.bloom_export("requirements", self.project, "csv")
        rows = {row[0]: row for row in answer.rows[1:]}
        self.print_variables({"header": answer.rows[0]})
        self.assertEqual(
            (
                answer.media_type.startswith("text/csv"),
                'filename="PRJ-requirements.csv"' in answer.disposition,
                answer.rows[0],
                rows["PRJ-REQ-001"][1:3],
                rows["PRJ-REQ-002"][1],
            ),
            (
                True,
                True,
                self.parameters.EXR_REQUIREMENT_HEADER,
                ["Login shall be possible", "Approved"],
                "Uncovered requirement",
            ),
            msg=self.parameters.MSG_EXR_CSV,
            abort_on_fail=False,
        )

    def bud_the_requirements_pdf_is_a_pdf(self):
        answer = self.bloom.bloom_export("requirements", self.project, "pdf")
        self.print_variables({"bytes": len(answer.body)})
        self.assertEqual(
            (
                answer.media_type,
                answer.body[:5],
                len(answer.body) > self.parameters.EXR_MIN_PDF_BYTES,
            ),
            ("application/pdf", b"%PDF-", True),
            msg=self.parameters.MSG_EXR_PDF,
            abort_on_fail=False,
        )

    def bud_the_traceability_csv_marks_coverage(self):
        answer = self.bloom.bloom_export("traceability", self.project, "csv")
        rows = {(row[0], row[3]): row for row in answer.rows[1:]}
        covered, uncovered = rows.get(("PRJ-REQ-001", "yes")), rows.get(("PRJ-REQ-002", "no"))
        self.print_variables({"rows": answer.rows})
        self.assertEqual(
            (answer.rows[0], covered[4], covered[6], uncovered[4]),
            (self.parameters.EXR_TRACE_HEADER, "PRJ-TC-001", "passed", ""),
            msg=self.parameters.MSG_EXR_TRACE,
            abort_on_fail=False,
        )

    def bud_an_export_of_a_missing_project_is_refused_404(self):
        answer = self.bloom.bloom_export("requirements", self.parameters.ETC_MISSING_PROJECT, "csv")
        self.assertEqual(
            answer.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_EXR_MISSING,
            abort_on_fail=False,
        )
