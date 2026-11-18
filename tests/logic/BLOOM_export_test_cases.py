"""
* @file     ${tests/logic/BLOOM_export_test_cases.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The test case export writes CSV, Markdown and XML, and refuses a missing project.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the export of a project holding two test cases.
"""

from tests.logic.export_test_cases import ExportTestCasesBase


class ExportTestCasesTest(ExportTestCasesBase):

    def setUpClass(self):
        super().setUpClass()
        self.project, _ = self.bloom.bloom_seed_export_cases()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ExportTestCasesTest().run()
