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
        self.tc_fields = {
            f"{artefact}{suffix}": self.bloom.bloom_schema_fields(f"{artefact}{suffix}")
            for artefact in self.parameters.RICH_CONTENT_TYPES
            for suffix in self.parameters.RICH_SCHEMA_SUFFIXES
        }
        self.tc_built = {
            f"{artefact}Create": self.bloom.bloom_build_schema(
                f"{artefact}Create", self.parameters.RICH_PAYLOAD
            )
            for artefact in self.parameters.RICH_CONTENT_TYPES
        }

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ArtefactRichContentTest().run()
