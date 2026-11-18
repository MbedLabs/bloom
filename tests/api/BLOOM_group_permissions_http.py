"""
* @file     ${tests/api/BLOOM_group_permissions_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Explicit project policies and whole artefact scopes are enforced over HTTP.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the routes on the full application with scenario policies; each step uses its own project and users.
"""

from tests.api.group_permissions_http import GroupPermissionsHttpBase


class GroupPermissionsHttpTest(GroupPermissionsHttpBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.bloom.bloom_limit_reqif_imports(100)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    GroupPermissionsHttpTest().run()
