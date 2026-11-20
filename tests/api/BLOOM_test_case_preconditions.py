"""
* @file     ${tests/api/BLOOM_test_case_preconditions.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A precondition sent to the test case routes in any accepted form is stored as a precondition row, and an unknown row type is refused.
* @author   Amine El Omari
* @date     2026-11-18
* @version  1.0.0
* @note     This module tests one project through the in-process API.
"""

from tests.api.test_case_preconditions import TestCasePreconditionsBase


class TestCasePreconditionsTest(TestCasePreconditionsBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.project = self.bloom.bloom_api_new_project(self.admin, self.parameters.PRE_PREFIX)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TestCasePreconditionsTest().run()
