"""
* @file     ${tests/logic/BLOOM_import_testrail.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A TestRail import creates draft cases, their suite and requirement links, and updates them on re-import.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the import into a project holding one requirement; each step starts from a new database.
"""

from tests.logic.import_testrail import ImportTestrailBase


class ImportTestrailTest(ImportTestrailBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ImportTestrailTest().run()
