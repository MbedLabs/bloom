"""
* @file     ${tests/api/perf_traceability.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the number of statements of the traceability reads.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the traceability statement counts.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class PerfTraceabilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_matrix_is_read_with_few_statements(self):
        project = self.bloom.bloom_api_new_project(self.admin, self.parameters.PERF_PREFIXES[0])
        self.bloom.bloom_api_add_requirements(
            self.admin, project["id"], self.parameters.PERF_REQUIREMENTS
        )
        answer, statements = self.bloom.bloom_api_count_statements(
            "GET", f"/api/traceability?project_id={project['id']}", self.admin
        )
        self.print_variables({"statements": statements})
        self.assertEqual(
            (answer.status, statements < self.parameters.PERF_STATEMENT_LIMIT),
            (self.parameters.STATUS_OK, True),
            msg=self.parameters.MSG_PERF_MATRIX,
            abort_on_fail=False,
            method="GET",
            endpoint=f"/api/traceability?project_id={project['id']}",
        )

    def bud_the_coverage_gaps_are_read_with_few_statements(self):
        project = self.bloom.bloom_api_new_project(self.admin, self.parameters.PERF_PREFIXES[1])
        self.bloom.bloom_api_add_requirements(
            self.admin, project["id"], self.parameters.PERF_REQUIREMENTS
        )
        answer, statements = self.bloom.bloom_api_count_statements(
            "GET", f"/api/traceability/coverage-gaps/{project['id']}", self.admin
        )
        self.print_variables({"statements": statements})
        self.assertEqual(
            (answer.status, statements < self.parameters.PERF_STATEMENT_LIMIT),
            (self.parameters.STATUS_OK, True),
            msg=self.parameters.MSG_PERF_GAPS,
            abort_on_fail=False,
            method="GET",
            endpoint=f"/api/traceability/coverage-gaps/{project['id']}",
        )

    def bud_a_requirement_is_read_with_few_statements(self):
        project = self.bloom.bloom_api_new_project(self.admin, self.parameters.PERF_PREFIXES[2])
        root = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={"project_id": project["id"], "title": "Root Req"},
        ).body
        answer, statements = self.bloom.bloom_api_count_statements(
            "GET", f"/api/requirements/{root['id']}", self.admin
        )
        self.print_variables({"statements": statements})
        self.assertEqual(
            (answer.status, statements < self.parameters.PERF_STATEMENT_LIMIT),
            (self.parameters.STATUS_OK, True),
            msg=self.parameters.MSG_PERF_DETAIL,
            abort_on_fail=False,
            method="GET",
            endpoint=f"/api/requirements/{root['id']}",
        )
