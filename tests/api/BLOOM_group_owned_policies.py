"""
* @file     ${tests/api/BLOOM_group_owned_policies.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Group-owned rules apply to admitted users without combining action and origin scopes.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests policies, groups and project entries on the full application; each step uses its own project and users.
"""

from tests.api.group_owned_policies import GroupOwnedPoliciesBase


class GroupOwnedPoliciesTest(GroupOwnedPoliciesBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    GroupOwnedPoliciesTest().run()
