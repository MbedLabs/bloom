"""
* @file     ${tests/logic/BLOOM_artefact_rich_content.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Every artefact the editor can open accepts and returns its rich content.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the create, update and response schemas of seven artefacts.
"""

from tests.logic.artefact_rich_content import ArtefactRichContentBase


class ArtefactRichContentTest(ArtefactRichContentBase):

    def setUpClass(self):
        super().setUpClass()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ArtefactRichContentTest().run()
