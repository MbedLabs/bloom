"""
* @file     ${tests/sec/traceability_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what an external reader gets of the traceability of a project.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the traceability an external reader reads.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class TraceabilityExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_gets_only_the_customer_pair(self):
        self.print_variables({"status": self.matrix.status, "body": self.matrix.body})
        self.assertEqual(
            (
                self.matrix.status,
                [
                    (
                        item["requirement"]["req_id"],
                        [tc["tc_id"] for tc in item["linked_test_cases"]],
                    )
                    for item in self.matrix.body["items"]
                ],
            ),
            (
                self.parameters.STATUS_OK,
                [(self.parameters.READER_CUSTOMER_REQ, [self.parameters.READER_CUSTOMER_TC])],
            ),
            msg=self.parameters.MSG_READER_MATRIX,
            abort_on_fail=False,
        )

    def bud_coverage_counts_only_the_customer_requirement(self):
        self.print_variables({"status": self.coverage.status, "body": self.coverage.body})
        self.assertEqual(
            (
                self.coverage.status,
                tuple(
                    self.coverage.body[key]
                    for key in ("total_requirements", "covered", "uncovered")
                ),
            ),
            (self.parameters.STATUS_OK, self.parameters.READER_COVERAGE),
            msg=self.parameters.MSG_READER_COVERAGE,
            abort_on_fail=False,
        )

    def bud_impact_of_an_internal_requirement_is_hidden_404(self):
        self.print_variables({"status": self.impact.status, "body": self.impact.body})
        self.assertEqual(
            self.impact.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_IMPACT_HIDDEN,
            abort_on_fail=False,
        )
