"""
* @file     ${tests/logic/BLOOM_vision_tags.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A Vision tags any kind, is tagged by any tag host, and Markdown VIS sections are filed as visions.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests tag links and the Markdown import with a vision; each step starts from a new database.
"""

from tests.logic.vision_tags import VisionTagsBase


class VisionTagsTest(VisionTagsBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    VisionTagsTest().run()
