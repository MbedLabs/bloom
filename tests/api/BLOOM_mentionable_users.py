"""
* @file     ${tests/api/BLOOM_mentionable_users.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A project member is offered the project's active members and the administrators, by identity only.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the mention list on the full application with seven people on two projects.
"""

from tests.api.mentionable_users import MentionableUsersBase


class MentionableUsersTest(MentionableUsersBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.world = self.bloom.bloom_new_mention_world()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    MentionableUsersTest().run()
