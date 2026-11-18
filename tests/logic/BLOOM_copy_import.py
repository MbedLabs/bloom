"""
* @file     ${tests/logic/BLOOM_copy_import.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Copied requirements and test cases become drafts after the target's highest id and name their source.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the copy with a source and a target project; each step starts from a new database.
"""

from tests.logic.copy_import import CopyImportBase


class CopyImportTest(CopyImportBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CopyImportTest().run()
