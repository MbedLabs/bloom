"""
* @file     ${tests/api/BLOOM_profile_picture.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An account uploads, reads, replaces and removes its own picture; uploads are checked and normalised.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the picture routes on the full application with two accounts; each step starts from a new database.
"""

from tests.api.profile_picture import ProfilePictureBase


class ProfilePictureTest(ProfilePictureBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProfilePictureTest().run()
