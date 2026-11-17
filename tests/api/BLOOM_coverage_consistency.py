"""
* @file     ${tests/api/BLOOM_coverage_consistency.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Coverage means the same thing wherever it is reported.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the coverage rule and its reports on the full application; each step uses its own project.
"""

from tests.api.coverage_consistency import CoverageConsistencyBase


class CoverageConsistencyTest(CoverageConsistencyBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CoverageConsistencyTest().run()
