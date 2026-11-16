"""
* @file     ${tests/logic/BLOOM_md_import.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Markdown is classified per document or section, parameters become placeholders, and name collisions are reported.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the Markdown parser on short documents.
"""

from tests.logic.md_import import MdImportBase


class MdImportTest(MdImportBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    MdImportTest().run()
