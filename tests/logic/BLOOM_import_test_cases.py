"""
* @file     ${tests/logic/BLOOM_import_test_cases.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A test case import updates and creates from CSV or XML, refuses approval and skips rows without a title.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the import into a project holding one draft test case; each step starts from a new database.
"""

from tests.logic.import_test_cases import ImportTestCasesBase


class ImportTestCasesTest(ImportTestCasesBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ImportTestCasesTest().run()
