"""
* @file     ${tests/api/BLOOM_traceability_coverage.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Requirements count as uncovered, partial or covered by the state of the test cases that verify them.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests one project with an unverified requirement, one verified by a draft and one by an approved test case.
"""

from tests.api.traceability_coverage import TraceabilityCoverageBase


class TraceabilityCoverageTest(TraceabilityCoverageBase):

    def setUpClass(self):
        super().setUpClass()
        values = self.parameters
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.project = self.bloom.bloom_api_new_project(self.admin, values.TCOV_PREFIX)["id"]
        _, partial, covered = (
            self.bloom.bloom_api_create_requirement(self.admin, self.project, title).json()["id"]
            for title in values.TCOV_TITLES
        )
        draft = self.bloom.bloom_api_add_test_case(
            self.admin, self.project, "Draft TC", status="Draft"
        ).body["id"]
        approved = self.bloom.bloom_api_add_test_case(
            self.admin, self.project, "Approved TC", status="Draft"
        ).body["id"]
        self.bloom.bloom_api_verify(self.admin, self.project, draft, partial)
        self.bloom.bloom_api_verify(self.admin, self.project, approved, covered)
        self.creator, self.signed = self.bloom.bloom_api_approve_test_case(self.admin, approved)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TraceabilityCoverageTest().run()
