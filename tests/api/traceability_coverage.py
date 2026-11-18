"""
* @file     ${tests/api/traceability_coverage.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the coverage state of requirements in the gap report and the matrix.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the traceability coverage.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class TraceabilityCoverageBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_test_case_is_approved_by_its_creator(self):
        creator, signed = self.bloom.bloom_api_approve_test_case(self.admin, self.approved_id)
        self.print_variables({"signed": signed.body})
        self.assertEqual(
            (signed.status, signed.body.get("reviewed_by_id"), signed.body.get("approved_by_id")),
            (self.parameters.STATUS_OK, creator, creator),
            msg=self.parameters.MSG_TCOV_APPROVED,
            abort_on_fail=False,
        )

    def bud_the_gap_report_counts_by_verification_state(self):
        path = f"/api/traceability/coverage-gaps/{self.project}"
        report = self.bloom.bloom_api_call("GET", path, self.admin)
        self.print_variables({"report": report.body})
        body = report.body
        self.assertEqual(
            (
                report.status,
                body["total_requirements"],
                body["uncovered"],
                body["partial"],
                body["covered"],
                body["coverage_percent"],
                len(body["gaps"]),
            ),
            (self.parameters.STATUS_OK, 3, 1, 1, 1, 66.7, 2),
            msg=self.parameters.MSG_TCOV_REPORT,
            abort_on_fail=False,
            method="GET",
            endpoint=path,
        )

    def bud_the_matrix_shows_each_coverage_state(self):
        matrix = self.bloom.bloom_api_call(
            "GET", "/api/traceability", self.admin, params={"project_id": self.project}
        )
        states = {
            item["requirement"]["title"]: item["coverage_status"] for item in matrix.body["items"]
        }
        self.assertEqual(
            (matrix.status, states),
            (self.parameters.STATUS_OK, {title: title for title in self.parameters.TCOV_TITLES}),
            msg=self.parameters.MSG_TCOV_MATRIX,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/traceability",
        )

    def bud_the_uncovered_filter_returns_one_requirement(self):
        filtered = self.bloom.bloom_api_call(
            "GET",
            "/api/traceability",
            self.admin,
            params={"project_id": self.project, "coverage_filter": "Uncovered"},
        )
        self.assertEqual(
            (filtered.status, filtered.body["total"], len(filtered.body["items"])),
            (self.parameters.STATUS_OK, 1, 1),
            msg=self.parameters.MSG_TCOV_FILTER,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/traceability",
        )

    def bud_sorting_by_coverage_orders_the_states(self):
        ordered = self.bloom.bloom_api_call(
            "GET",
            "/api/traceability",
            self.admin,
            params={"project_id": self.project, "sort_by": "coverage"},
        )
        self.assertEqual(
            (ordered.status, [item["coverage_status"] for item in ordered.body["items"]]),
            (self.parameters.STATUS_OK, list(self.parameters.TCOV_TITLES)),
            msg=self.parameters.MSG_TCOV_SORT,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/traceability",
        )
