"""
* @file     ${tests/api/BLOOM_groups_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A group grant gives its members the granted project; default policies are protected and the routes are for administrators.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the groups and policies routes on the full application with the built-in catalogue.
"""

from tests.api.groups_http import GroupsHttpBase


class GroupsHttpTest(GroupsHttpBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.bloom.bloom_seed_default_catalogue()
        self.bloom.bloom_enforce_foreign_keys()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    GroupsHttpTest().run()
