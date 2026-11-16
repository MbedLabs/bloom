"""
* @file     ${tests/logic/BLOOM_import_markdown.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A Markdown import creates artefacts and parameters, and a colliding parameter name needs a chosen action first.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the import into a project holding the parameter BOOT_MS; each step starts from a new database.
"""

from tests.logic.import_markdown import ImportMarkdownBase


class ImportMarkdownTest(ImportMarkdownBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ImportMarkdownTest().run()
