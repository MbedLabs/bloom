"""
* @file     ${tests/api/BLOOM_user_deletion.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Deleting a user removes the user, also when the user is a project member.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the user delete route of the full app in-process.
"""

from tests.api.user_deletion import UserDeletionBase


class UserDeletionTest(UserDeletionBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_enforce_foreign_keys()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        self.admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        plain_email, member_email = self.parameters.DELETION_EMAILS
        self.plain = self._create(plain_email)
        self.member = self._create(member_email)
        project = self.bloom.bloom_api_create_project(
            self.admin, self.parameters.DELETION_PREFIX
        ).json()
        policy = self.bloom.bloom_api_create_policy(
            self.admin,
            self.parameters.DELETION_POLICY,
            self.parameters.DELETION_PERMISSIONS,
            self.parameters.DELETION_DOC_TYPES,
            visibility=self.parameters.DELETION_VISIBILITY,
        ).json()
        self.membership = self.bloom.bloom_api_add_project_member(
            self.admin, project.get("id"), self.member.json().get("id"), [policy.get("id")]
        )

    def tearDownClass(self):
        super().tearDownClass()

    def _create(self, email):
        """Create a user with the deletion role."""
        return self.bloom.bloom_api_create_user(
            self.admin, email, self.parameters.API_PASSWORD, self.parameters.DELETION_ROLE
        )


if __name__ == "__main__":
    UserDeletionTest().run()
