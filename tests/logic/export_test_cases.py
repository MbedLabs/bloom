"""
* @file     ${tests/logic/export_test_cases.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the test case export as CSV, Markdown and XML.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the test case export.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ExportTestCasesBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_the_csv_export_holds_the_test_cases(self):
        answer = self.bloom.bloom_export_test_cases(self.project, "csv")
        rows = answer.rows
        steps = rows[0].index("steps")
        first = {row[0]: row for row in rows[1:]}[self.parameters.ETC_FIRST]
        self.print_variables({"header": rows[0]})
        self.assertEqual(
            (
                answer.media_type.startswith("text/csv"),
                'filename="PRJ-test-cases.csv"' in answer.disposition,
                rows[0][:3],
                first[1],
                "Open login => Form shown" in first[steps],
            ),
            (True, True, ["tc_id", "title", "status"], "Verify login", True),
            msg=self.parameters.MSG_ETC_CSV,
            abort_on_fail=False,
        )

    def bud_the_markdown_export_holds_the_test_cases(self):
        answer = self.bloom.bloom_export_test_cases(self.project, "md")
        body = answer.body
        self.print_variables({"start": body[:80]})
        self.assertEqual(
            (
                answer.media_type.startswith("text/markdown"),
                'filename="PRJ-test-cases.md"' in answer.disposition,
                body.startswith("Test cases of Demo (PRJ)"),
                "## [TC] Verify login" in body,
                "- Pre-Condition: User exists" in body,
                "- Step: Open login => Form shown" in body,
            ),
            (True,) * 6,
            msg=self.parameters.MSG_ETC_MARKDOWN,
            abort_on_fail=False,
        )

    def bud_the_xml_export_is_well_formed(self):
        answer = self.bloom.bloom_export_test_cases(self.project, "xml")
        root = answer.xml
        self.assertEqual(
            (
                answer.media_type.startswith("application/xml"),
                root.tag,
                [tc.get("id") for tc in root.findall("test-case")],
                root.find("test-case").findtext("title"),
            ),
            (
                True,
                "test-cases",
                [self.parameters.ETC_FIRST, self.parameters.ETC_SECOND],
                "Verify login",
            ),
            msg=self.parameters.MSG_ETC_XML,
            abort_on_fail=False,
        )

    def bud_an_export_of_a_missing_project_is_refused_404(self):
        answer = self.bloom.bloom_export_test_cases(self.parameters.ETC_MISSING_PROJECT, "csv")
        self.assertEqual(
            answer.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_ETC_MISSING,
            abort_on_fail=False,
        )
