"""
* @file     ${tests/logic/BLOOM_artefact_creator.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Each artefact records internally who created it, and no response carries the record.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests creation, imports, Jira defects, Bud reports and user deletion; each step starts from a new database.
"""

from tests.logic.artefact_creator import ArtefactCreatorBase


class ArtefactCreatorTest(ArtefactCreatorBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ArtefactCreatorTest().run()
