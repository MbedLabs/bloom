"""
* @file     ${tests/logic/BLOOM_id_generator.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Document ids continue after the highest, widen past 999, and refuse bad prefixes, types and projects.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the id functions with lists of existing ids.
"""

from tests.logic.id_generator import IdGeneratorBase


class IdGeneratorTest(IdGeneratorBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IdGeneratorTest().run()
