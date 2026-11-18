"""
* @file     ${tests/logic/BLOOM_import_markdown_formatting.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Imported Markdown is shown formatted: it becomes the editor's rich content with parameter chips, and a declaration sets the parameter kind.
* @author   Amine El Omari
* @date     2026-11-18
* @version  1.0.0
* @note     This module tests the import into a project holding the variable BOOT_MS; each step starts from a new database.
"""

from tests.logic.import_markdown_formatting import ImportMarkdownFormattingBase


class ImportMarkdownFormattingTest(ImportMarkdownFormattingBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ImportMarkdownFormattingTest().run()
