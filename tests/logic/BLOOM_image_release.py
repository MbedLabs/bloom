"""
* @file     ${tests/logic/BLOOM_image_release.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Release promotion moves only the tags it may, keeps digests, and inspects only well-formed references.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests scripts/image_release.py with docker replaced.
"""

from tests.logic.image_release import ImageReleaseBase


class ImageReleaseTest(ImageReleaseBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ImageReleaseTest().run()
