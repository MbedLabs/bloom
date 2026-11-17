"""
* @file     ${tests/api/BLOOM_user_identity_picture.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Current pictures accompany identities through existing authenticated read scopes.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the identity reads on the full application with three people; each step starts from a new database.
"""

from tests.api.user_identity_picture import UserIdentityPictureBase


class UserIdentityPictureTest(UserIdentityPictureBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    UserIdentityPictureTest().run()
